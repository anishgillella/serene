"""
AWS S3 service for storing files
"""
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO
from app.config import settings

logger = logging.getLogger(__name__)

class S3Service:
    """Service for interacting with AWS S3"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME
        logger.info(f"✅ Initialized S3 client for bucket: {self.bucket_name}")
    
    def upload_file(
        self,
        file_path: str,
        file_content: bytes,
        content_type: str = "application/json"
    ) -> Optional[str]:
        """
        Upload file to S3
        
        Args:
            file_path: Path in S3 (e.g., "transcripts/relationship_id/conflict_id.json")
            file_content: File content as bytes
            content_type: MIME type of the file
        
        Returns:
            S3 URL if successful, None otherwise
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_path,
                Body=file_content,
                ContentType=content_type
            )
            
            # Generate S3 URL
            s3_url = f"s3://{self.bucket_name}/{file_path}"
            logger.info(f"✅ Uploaded file to S3: {file_path}")
            return s3_url
        except ClientError as e:
            logger.error(f"❌ Error uploading file to S3: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error uploading to S3: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def download_file(self, file_path: str) -> Optional[bytes]:
        """
        Download file from S3
        
        Args:
            file_path: Path in S3 (e.g., "transcripts/relationship_id/conflict_id.json")
        
        Returns:
            File content as bytes if successful, None otherwise
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            file_content = response['Body'].read()
            logger.info(f"✅ Downloaded file from S3: {file_path}")
            return file_content
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"⚠️ File not found in S3: {file_path}")
            else:
                logger.error(f"❌ Error downloading file from S3: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error downloading from S3: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists in S3"""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"❌ Error checking file existence in S3: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error checking file in S3: {e}")
            return False
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_path
            )
            logger.info(f"✅ Deleted file from S3: {file_path}")
            return True
        except ClientError as e:
            logger.error(f"❌ Error deleting file from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error deleting from S3: {e}")
            return False
    
    def get_file_url(self, file_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Generate presigned URL for file access
        
        Args:
            file_path: Path in S3
            expires_in: URL expiration time in seconds (default 1 hour)
        
        Returns:
            Presigned URL if successful, None otherwise
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_path
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"❌ Error generating presigned URL: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error generating presigned URL: {e}")
            return None

# Singleton instance
s3_service = S3Service()







