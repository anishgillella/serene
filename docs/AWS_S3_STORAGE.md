# AWS S3 Storage Architecture

## Overview

All files are stored directly in **AWS S3**, and only the S3 paths/URLs are stored in the Supabase database.

---

## Storage Architecture

### Triple Storage Pattern

1. **AWS S3** - Raw files (PDFs, JSON transcripts, analysis, repair plans)
2. **Supabase Database** - Metadata and S3 paths/URLs
3. **Pinecone** - Vector embeddings for semantic search

---

## S3 Bucket Structure

**Bucket Name**: `serene-relationship-mediator` (configurable via `S3_BUCKET_NAME`)

```
serene-relationship-mediator/
├── transcripts/
│   └── {relationship_id}/
│       └── {conflict_id}.json
├── profiles/
│   └── {relationship_id}/
│       └── {pdf_id}.pdf
├── handbooks/
│   └── {relationship_id}/
│       └── {pdf_id}.pdf
├── analysis/
│   └── {relationship_id}/
│       └── {conflict_id}_analysis.json
└── repair_plans/
    └── {relationship_id}/
        ├── {conflict_id}_repair_partner_a.json
        └── {conflict_id}_repair_partner_b.json
```

---

## File Paths Stored in Database

### Transcripts
- **Database Field**: `conflicts.transcript_path`
- **S3 Path**: `transcripts/{relationship_id}/{conflict_id}.json`
- **Stored Value**: S3 URL (`s3://bucket/path`) or S3 key path

### Profiles
- **Database Field**: `profiles.file_path`
- **S3 Path**: `profiles/{relationship_id}/{pdf_id}.pdf` or `handbooks/{relationship_id}/{pdf_id}.pdf`
- **Stored Value**: S3 URL or S3 key path

### Analysis
- **Database Field**: `conflict_analysis.analysis_path`
- **S3 Path**: `analysis/{relationship_id}/{conflict_id}_analysis.json`
- **Stored Value**: S3 URL or S3 key path

### Repair Plans
- **Database Field**: `repair_plans.plan_path`
- **S3 Path**: `repair_plans/{relationship_id}/{conflict_id}_repair_{partner_id}.json`
- **Stored Value**: S3 URL or S3 key path

---

## Environment Variables

Add these to your `.env` file:

```bash
# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-east-1  # or your preferred region
S3_BUCKET_NAME=serene-relationship-mediator
```

---

## S3 Service

The `S3Service` class (`backend/app/services/s3_service.py`) handles all S3 operations:

- `upload_file()` - Upload files to S3
- `download_file()` - Download files from S3
- `file_exists()` - Check if file exists
- `delete_file()` - Delete files from S3
- `get_file_url()` - Generate presigned URLs

---

## Data Flow

### Upload Profile PDF
```
1. User uploads PDF → FastAPI endpoint
2. Extract text via OCR → Mistral
3. Generate embedding → Voyage-3
4. Upload PDF to S3 → s3_service.upload_file()
5. Store S3 URL in Supabase DB → profiles table
6. Store vector in Pinecone → profiles namespace
```

### Store Conflict Transcript
```
1. Fight ends → Transcript segments collected
2. Upload JSON to S3 → s3_service.upload_file()
3. Store S3 URL in Supabase DB → conflicts table
4. Generate embedding → Voyage-3
5. Store vector in Pinecone → transcripts namespace
```

### Generate Analysis
```
1. Analysis generated → LLM (OpenRouter)
2. Upload JSON to S3 → s3_service.upload_file()
3. Store S3 URL in Supabase DB → conflict_analysis table
4. Generate embedding → Voyage-3
5. Store vector in Pinecone → analysis namespace
```

---

## Path Format Handling

The code handles multiple path formats for backward compatibility:

1. **S3 URL**: `s3://bucket-name/path/to/file.json`
2. **S3 Key**: `transcripts/relationship_id/conflict_id.json`
3. **Legacy format**: `relationship_id/conflict_id.json` (auto-prefixed)

When reading files, the code automatically:
- Extracts S3 key from S3 URLs
- Adds folder prefixes if missing
- Handles both old and new formats

---

## Benefits

✅ **Direct AWS S3** - Full control over storage  
✅ **Scalable** - S3 handles unlimited storage  
✅ **Cost-effective** - Pay only for what you use  
✅ **Reliable** - 99.999999999% (11 9's) durability  
✅ **Fast** - CDN integration possible  
✅ **Secure** - IAM policies, encryption at rest  

---

## Setup Steps

1. **Create S3 Bucket**:
   - Name: `serene-relationship-mediator`
   - Region: Your preferred region (e.g., `us-east-1`)
   - Versioning: Optional (recommended for backups)

2. **Configure IAM User**:
   - Create IAM user with S3 access
   - Attach policy: `AmazonS3FullAccess` (or custom policy)
   - Generate access keys

3. **Add Environment Variables**:
   ```bash
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=serene-relationship-mediator
   ```

4. **Test Upload**:
   ```python
   from app.services.s3_service import s3_service
   s3_service.upload_file("test/test.json", b'{"test": "data"}')
   ```

---

## Migration Notes

- Old Supabase Storage paths are automatically converted to S3 paths
- Database stores S3 URLs or paths (both formats supported)
- Code handles backward compatibility with old path formats







