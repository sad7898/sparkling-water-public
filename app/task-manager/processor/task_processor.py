import boto3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import AWS_REGION, DATA_BUCKET_NAME, EMR_SCRIPT_PATH, EMR_SERVERLESS_APPLICATION_ID, EMR_EXECUTION_ROLE_ARN
logger = logging.getLogger(__name__)

class TaskProcessor:
    def __init__(self, event: Optional[Dict[str, Any]] = None):
        self.emr_serverless = boto3.client('emr-serverless', region_name=AWS_REGION)
        self.event = event or {}

    def __format_datetime_path(self, dt):
        return f"{dt.year:04d}/{dt.month:02d}/{dt.day:02d}/{dt.hour:02d}"
    
    def __parse_event(self):
        messages = []
        for message in self.event.get('Records', []):
            body = json.loads(message['body'])
            for record in body.get('Records', []):
                s3_info = record.get('s3', {})
                bucket_name = s3_info.get('bucket', {}).get('name')
                object_key = s3_info.get('object', {}).get('key')
                if bucket_name and object_key:
                    messages.append({
                        'bucket_name': bucket_name,
                        'object_key': object_key,
                        'messageId':  message.get("messageId")
                    })
        
        return messages
    
    def __group_messages_by_datetime(self, s3_notifications: List[Dict]) -> Dict[datetime, List[Dict]]:
        message_partitions = {}
        for notification in s3_notifications:
            partition = "/".join(notification['object_key'].split('/')[3:7])
            partition_datetime = datetime.strptime(partition, "%Y/%m/%d/%H")
            if partition_datetime not in message_partitions:
                message_partitions[partition_datetime] = [notification]
            else:
                message_partitions[partition_datetime].append(notification)
        return message_partitions

    def process(self):
        s3_notifications = self.__parse_event()
        message_partitions = self.__group_messages_by_datetime(s3_notifications)
        response = {
            "total": len(message_partitions),
            "completed": 0,
            "failures":{
                "batchItemFailures": [],
                "partitions": []
            }
        }
        for partition, notifications in message_partitions.items():
            try:
                print(partition)
                formatted_partition = self.__format_datetime_path(partition)
                running_jobs = self.emr_serverless.list_job_runs(
                    applicationId=EMR_SERVERLESS_APPLICATION_ID,
                    states=['SUBMITTED', 'PENDING', 'SCHEDULED', 'RUNNING', 'QUEUED'],
                    mode="BATCH",
                    maxResults=50
                )
                if formatted_partition in [job['name'] for job in running_jobs.get('jobRuns', [])]:
                    logger.info(f"EMR job for partition {partition} is already running. Skipping submission.")
                    response["completed"] +=1
                    continue
                self.submit_emr_job(partition=formatted_partition, 
                                    script_path=EMR_SCRIPT_PATH)
                response["completed"] +=1
            except Exception as ex:
                logger.error(str(ex))
                logger.error(f"Failed to submit EMR job for partition {partition}")
                response['failures']['batchItemFailures'].append({"itemIdentifiers": notifications[0].get("messageId")})
                response['failures']["partitions"].append(partition)
        return response
    
    def submit_emr_job(self, partition: str, script_path: str, entry_point_args=[]) -> str:
        response = self.emr_serverless.start_job_run(
            name=partition,
            applicationId=EMR_SERVERLESS_APPLICATION_ID,
            executionRoleArn=EMR_EXECUTION_ROLE_ARN,
            jobDriver={
                'sparkSubmit': {
                        'entryPoint': f's3://{DATA_BUCKET_NAME}/{script_path}',
                        'entryPointArguments': entry_point_args + [f"s3://{DATA_BUCKET_NAME}/raw/reddit/cryptocurrency/{partition}"] + [f"s3://{DATA_BUCKET_NAME}/processed/reddit/{partition}"]
                }
            },
            configurationOverrides={
                'applicationConfiguration': [
                    {
                        'classification': 'spark-defaults',
                        'properties': {
                            'spark.executor.instances': '1',
                            'spark.executor.memory': '2G',
                            'spark.executor.cores': '2',
                            'spark.dynamicAllocation.maxExecutors': '3',
                            'spark.dynamicAllocation.initialExecutors': '1',
                            'spark.executorEnv.PYSPARK_PYTHON': './environment/bin/pythonspark.dynamicAllocation.maxExecutors=3',
                            'spark.emr-serverless.driverEnv.PYSPARK_PYTHON': './environment/bin/python',
                            'spark.emr-serverless.driverEnv.PYSPARK_DRIVER_PYTHON': './environment/bin/python',
                            'spark.executor.instances': '2',
                            'spark.archives': f's3://{DATA_BUCKET_NAME}/spark_jobs/dependencies/spark_venv.tar.gz#environment'
    
                        }
                    }
                ]
            }
        )
        logger.info(f"Submitted EMR job for partition {partition}: {response['jobRunId']}")
        return response['jobRunId']
            