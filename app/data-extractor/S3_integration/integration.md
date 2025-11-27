### Integration

#### Example:
```python
from S3_integration.save_to_s3 import save_to_s3

# After processing Reddit data
reddit_data = [...]  # List of posts/comments
save_to_s3(reddit_data, source_name="reddit")
```

#### coingecko_pipeline.py
```python
from S3_integration.save_to_s3 import save_to_s3

# After processing CoinGecko data
# instead of save_to_s3()
result = save_to_s3(coin_data, source_name="coingecko")
return result
```

