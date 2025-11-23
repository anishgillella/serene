#!/usr/bin/env python3
"""
Ground Truth Query Script

Query and compare data from all 3 sources for ground truth verification.
Shows data from Database, Storage, and Pinecone side-by-side.

Usage:
    python scripts/query_ground_truth.py --conflict-id CONFLICT_ID
    python scripts/query_ground_truth.py --profile-id PROFILE_ID
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv(".env")

from supabase import create_client, Client
from app.config import settings
from app.services.pinecone_service import pinecone_service
from app.services.db_service import db_service
from app.services.s3_service import s3_service

class GroundTruthQuery:
    """Query ground truth data from all sources"""
    
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    def query_conflict(self, conflict_id: str) -> Dict[str, Any]:
        """Query conflict from all 3 sources"""
        result = {
            "conflict_id": conflict_id,
            "database": None,
            "storage": None,
            "pinecone": None
        }
        
        # Query database
        try:
            db_result = self.supabase.table("conflicts").select("*").eq("id", conflict_id).execute()
            if db_result.data:
                result["database"] = db_result.data[0]
        except Exception as e:
            result["database"] = {"error": str(e)}
        
        # Query storage (S3)
        if result["database"] and result["database"].get("transcript_path"):
            try:
                transcript_path = result["database"]["transcript_path"]
                # Extract S3 key from S3 URL if it's a full URL
                if transcript_path.startswith("s3://"):
                    s3_key = transcript_path.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                elif transcript_path.startswith("transcripts/"):
                    s3_key = transcript_path
                elif "/" in transcript_path:
                    s3_key = transcript_path
                else:
                    s3_key = f"transcripts/{transcript_path}"
                
                file_response = s3_service.download_file(s3_key)
                if file_response:
                    result["storage"] = json.loads(file_response.decode('utf-8'))
            except Exception as e:
                result["storage"] = {"error": str(e)}
        
        # Query Pinecone
        try:
            pinecone_result = pinecone_service.get_by_conflict_id(conflict_id, namespace="transcripts")
            if pinecone_result and pinecone_result.metadata:
                result["pinecone"] = {
                    "metadata": pinecone_result.metadata,
                    "transcript_preview": pinecone_result.metadata.get("transcript_text", "")[:200] + "..." if len(pinecone_result.metadata.get("transcript_text", "")) > 200 else pinecone_result.metadata.get("transcript_text", "")
                }
        except Exception as e:
            result["pinecone"] = {"error": str(e)}
        
        return result
    
    def query_analysis(self, conflict_id: str) -> Dict[str, Any]:
        """Query analysis from all 3 sources"""
        result = {
            "conflict_id": conflict_id,
            "type": "analysis",
            "database": None,
            "storage": None,
            "pinecone": None
        }
        
        # Query database
        try:
            db_result = self.supabase.table("conflict_analysis").select("*").eq("conflict_id", conflict_id).execute()
            if db_result.data:
                result["database"] = db_result.data[0]
        except Exception as e:
            result["database"] = {"error": str(e)}
        
        # Query storage (S3)
        if result["database"] and result["database"].get("analysis_path"):
            try:
                analysis_path = result["database"]["analysis_path"]
                # Extract S3 key from S3 URL if it's a full URL
                if analysis_path.startswith("s3://"):
                    s3_key = analysis_path.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                elif analysis_path.startswith("analysis/"):
                    s3_key = analysis_path
                elif "/" in analysis_path:
                    s3_key = analysis_path
                else:
                    s3_key = f"analysis/{analysis_path}"
                
                file_response = s3_service.download_file(s3_key)
                if file_response:
                    result["storage"] = json.loads(file_response.decode('utf-8'))
            except Exception as e:
                result["storage"] = {"error": str(e)}
        
        # Query Pinecone
        try:
            pinecone_result = pinecone_service.get_by_conflict_id(conflict_id, namespace="analysis")
            if pinecone_result and pinecone_result.metadata:
                result["pinecone"] = {
                    "metadata": pinecone_result.metadata,
                    "analysis_preview": pinecone_result.metadata.get("full_analysis_json", "")[:200] + "..." if len(pinecone_result.metadata.get("full_analysis_json", "")) > 200 else pinecone_result.metadata.get("full_analysis_json", "")
                }
        except Exception as e:
            result["pinecone"] = {"error": str(e)}
        
        return result
    
    def query_repair_plan(self, conflict_id: str, partner_id: str) -> Dict[str, Any]:
        """Query repair plan from all 3 sources"""
        result = {
            "conflict_id": conflict_id,
            "partner_id": partner_id,
            "type": "repair_plan",
            "database": None,
            "storage": None,
            "pinecone": None
        }
        
        # Query database
        try:
            db_result = self.supabase.table("repair_plans").select("*").eq("conflict_id", conflict_id).eq("partner_requesting", partner_id).execute()
            if db_result.data:
                result["database"] = db_result.data[0]
        except Exception as e:
            result["database"] = {"error": str(e)}
        
        # Query storage (S3)
        if result["database"] and result["database"].get("plan_path"):
            try:
                plan_path = result["database"]["plan_path"]
                # Extract S3 key from S3 URL if it's a full URL
                if plan_path.startswith("s3://"):
                    s3_key = plan_path.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                elif plan_path.startswith("repair_plans/"):
                    s3_key = plan_path
                elif "/" in plan_path:
                    s3_key = plan_path
                else:
                    s3_key = f"repair_plans/{plan_path}"
                
                file_response = s3_service.download_file(s3_key)
                if file_response:
                    result["storage"] = json.loads(file_response.decode('utf-8'))
            except Exception as e:
                result["storage"] = {"error": str(e)}
        
        # Query Pinecone
        try:
            pinecone_id = f"{conflict_id}_{partner_id}"
            pinecone_result = pinecone_service.get_by_conflict_id(pinecone_id, namespace="repair_plans")
            if pinecone_result and pinecone_result.metadata:
                result["pinecone"] = {
                    "metadata": pinecone_result.metadata,
                    "plan_preview": pinecone_result.metadata.get("full_repair_plan_json", "")[:200] + "..." if len(pinecone_result.metadata.get("full_repair_plan_json", "")) > 200 else pinecone_result.metadata.get("full_repair_plan_json", "")
                }
        except Exception as e:
            result["pinecone"] = {"error": str(e)}
        
        return result
    
    def query_profile(self, profile_id: str) -> Dict[str, Any]:
        """Query profile from all 3 sources"""
        result = {
            "profile_id": profile_id,
            "type": "profile",
            "database": None,
            "storage": None,
            "pinecone": None
        }
        
        # Query database
        try:
            profile = db_service.get_profile_by_id(profile_id)
            if profile:
                result["database"] = profile
        except Exception as e:
            result["database"] = {"error": str(e)}
        
        # Query storage (S3)
        if result["database"] and result["database"].get("file_path"):
            try:
                file_path = result["database"]["file_path"]
                # Extract S3 key from S3 URL if it's a full URL
                if file_path.startswith("s3://"):
                    s3_key = file_path.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                elif any(file_path.startswith(f"{folder}/") for folder in ["profiles", "handbooks"]):
                    s3_key = file_path
                elif "/" in file_path:
                    s3_key = file_path
                else:
                    folder = "profiles" if result["database"].get("pdf_type") in ["boyfriend_profile", "girlfriend_profile"] else "handbooks"
                    s3_key = f"{folder}/{file_path}"
                
                file_response = s3_service.download_file(s3_key)
                if file_response:
                    result["storage"] = {
                        "file_size": len(file_response),
                        "file_type": "PDF",
                        "s3_key": s3_key,
                        "note": "PDF file stored in S3 (binary data)"
                    }
            except Exception as e:
                result["storage"] = {"error": str(e)}
        
        # Query Pinecone
        if result["database"] and result["database"].get("pdf_id") and result["database"].get("pdf_type"):
            try:
                namespace = "profiles" if result["database"]["pdf_type"] in ["boyfriend_profile", "girlfriend_profile"] else "handbooks"
                vector_id = f"{result['database']['pdf_type']}_{result['database']['pdf_id']}"
                fetch_result = pinecone_service.index.fetch(ids=[vector_id], namespace=namespace)
                if fetch_result.vectors and vector_id in fetch_result.vectors:
                    vector_data = fetch_result.vectors[vector_id]
                    result["pinecone"] = {
                        "metadata": vector_data.get("metadata", {}),
                        "text_preview": vector_data.get("metadata", {}).get("extracted_text", "")[:200] + "..." if len(vector_data.get("metadata", {}).get("extracted_text", "")) > 200 else vector_data.get("metadata", {}).get("extracted_text", "")
                    }
            except Exception as e:
                result["pinecone"] = {"error": str(e)}
        
        return result
    
    def print_result(self, result: Dict[str, Any]):
        """Print formatted result"""
        print("\n" + "="*80)
        print(f"GROUND TRUTH QUERY: {result.get('conflict_id', result.get('profile_id', 'Unknown'))}")
        print("="*80)
        
        for source in ["database", "storage", "pinecone"]:
            print(f"\n📦 {source.upper()}:")
            if result.get(source):
                if isinstance(result[source], dict) and "error" in result[source]:
                    print(f"  ❌ Error: {result[source]['error']}")
                else:
                    print(json.dumps(result[source], indent=2, default=str))
            else:
                print("  ⚠️  No data")


def main():
    parser = argparse.ArgumentParser(description="Query ground truth data from all sources")
    parser.add_argument("--conflict-id", help="Query conflict by ID")
    parser.add_argument("--profile-id", help="Query profile by ID")
    parser.add_argument("--analysis", action="store_true", help="Also query analysis")
    parser.add_argument("--repair-plans", action="store_true", help="Also query repair plans")
    
    args = parser.parse_args()
    
    if not args.conflict_id and not args.profile_id:
        parser.print_help()
        return
    
    query = GroundTruthQuery()
    
    if args.conflict_id:
        result = query.query_conflict(args.conflict_id)
        query.print_result(result)
        
        if args.analysis:
            analysis_result = query.query_analysis(args.conflict_id)
            query.print_result(analysis_result)
        
        if args.repair_plans:
            for partner_id in ["partner_a", "partner_b"]:
                plan_result = query.query_repair_plan(args.conflict_id, partner_id)
                query.print_result(plan_result)
    
    elif args.profile_id:
        result = query.query_profile(args.profile_id)
        query.print_result(result)


if __name__ == "__main__":
    main()

