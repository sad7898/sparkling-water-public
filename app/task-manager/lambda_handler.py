import json
import logging
from processor.task_processor import TaskProcessor
from config import SQS_QUEUE_URL

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def handle(event, context):
    try:
        task_processor = TaskProcessor(event)
        results = task_processor.process()
        
        logger.info(f"Lambda processing completed: {results}")
        return results.get("batchItemFailures")
        
    except Exception as e:
        logger.error(f"Error in lambda handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Processing failed',
                'error': str(e)
            })
        }