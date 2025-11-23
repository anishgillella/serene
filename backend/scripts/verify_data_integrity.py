#!/usr/bin/env python3
"""
Data Integrity Verification Script

Verifies that all data exists in all 3 storage locations:
1. Supabase Database (metadata)
2. Supabase Storage (raw files)
3. Pinecone (vector embeddings)

Usage:
    python scripts/verify_data_integrity.py [--conflict-id CONFLICT_ID] [--relationship-id REL_ID]
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

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

class DataIntegrityChecker:
    """Check data integrity across all storage systems"""
    
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self.issues: List[Dict[str, Any]] = []
    
    def check_conflict(self, conflict_id: str) -> Dict[str, Any]:
        """Check if conflict exists in all 3 places"""
        result = {
            "conflict_id": conflict_id,
            "database": False,
            "storage": False,
            "pinecone": False,
            "issues": []
        }
        
        # Check database
        try:
            db_result = self.supabase.table("conflicts").select("*").eq("id", conflict_id).execute()
            if db_result.data:
                result["database"] = True
                conflict = db_result.data[0]
                result["relationship_id"] = conflict.get("relationship_id")
                result["transcript_path"] = conflict.get("transcript_path")
            else:
                result["issues"].append("Missing in database")
        except Exception as e:
            result["issues"].append(f"Database error: {e}")
        
        # Check storage (S3)
        if result.get("transcript_path"):
            try:
                transcript_path = result["transcript_path"]
                # Extract S3 key from S3 URL if it's a full URL
                if transcript_path.startswith("s3://"):
                    s3_key = transcript_path.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                elif transcript_path.startswith("transcripts/"):
                    s3_key = transcript_path
                elif "/" in transcript_path:
                    s3_key = transcript_path
                else:
                    s3_key = f"transcripts/{transcript_path}"
                
                file_exists = s3_service.file_exists(s3_key)
                if file_exists:
                    result["storage"] = True
                else:
                    result["issues"].append(f"Missing in S3: {s3_key}")
            except Exception as e:
                result["issues"].append(f"S3 error: {e}")
        else:
            result["issues"].append("No transcript_path in database")
        
        # Check Pinecone
        try:
            pinecone_result = pinecone_service.get_by_conflict_id(conflict_id, namespace="transcripts")
            if pinecone_result and pinecone_result.metadata:
                result["pinecone"] = True
            else:
                result["issues"].append("Missing in Pinecone (transcripts namespace)")
        except Exception as e:
            result["issues"].append(f"Pinecone error: {e}")
        
        return result
    
    def check_analysis(self, conflict_id: str) -> Dict[str, Any]:
        """Check if analysis exists in all 3 places"""
        result = {
            "conflict_id": conflict_id,
            "type": "analysis",
            "database": False,
            "storage": False,
            "pinecone": False,
            "issues": []
        }
        
        # Check database
        try:
            db_result = self.supabase.table("conflict_analysis").select("*").eq("conflict_id", conflict_id).execute()
            if db_result.data:
                result["database"] = True
                analysis = db_result.data[0]
                result["analysis_path"] = analysis.get("analysis_path")
            else:
                result["issues"].append("Missing in database")
        except Exception as e:
            result["issues"].append(f"Database error: {e}")
        
        # Check storage (S3)
        if result.get("analysis_path"):
            try:
                analysis_path = result["analysis_path"]
                # Extract S3 key from S3 URL if it's a full URL
                if analysis_path.startswith("s3://"):
                    s3_key = analysis_path.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                elif analysis_path.startswith("analysis/"):
                    s3_key = analysis_path
                elif "/" in analysis_path:
                    s3_key = analysis_path
                else:
                    s3_key = f"analysis/{analysis_path}"
                
                file_exists = s3_service.file_exists(s3_key)
                if file_exists:
                    result["storage"] = True
                else:
                    result["issues"].append(f"Missing in S3: {s3_key}")
            except Exception as e:
                result["issues"].append(f"S3 error: {e}")
        else:
            result["issues"].append("No analysis_path in database")
        
        # Check Pinecone
        try:
            pinecone_result = pinecone_service.get_by_conflict_id(conflict_id, namespace="analysis")
            if pinecone_result and pinecone_result.metadata:
                result["pinecone"] = True
            else:
                result["issues"].append("Missing in Pinecone (analysis namespace)")
        except Exception as e:
            result["issues"].append(f"Pinecone error: {e}")
        
        return result
    
    def check_repair_plan(self, conflict_id: str, partner_id: str) -> Dict[str, Any]:
        """Check if repair plan exists in all 3 places"""
        result = {
            "conflict_id": conflict_id,
            "partner_id": partner_id,
            "type": "repair_plan",
            "database": False,
            "storage": False,
            "pinecone": False,
            "issues": []
        }
        
        # Check database
        try:
            db_result = self.supabase.table("repair_plans").select("*").eq("conflict_id", conflict_id).eq("partner_requesting", partner_id).execute()
            if db_result.data:
                result["database"] = True
                plan = db_result.data[0]
                result["plan_path"] = plan.get("plan_path")
            else:
                result["issues"].append("Missing in database")
        except Exception as e:
            result["issues"].append(f"Database error: {e}")
        
        # Check storage (S3)
        if result.get("plan_path"):
            try:
                plan_path = result["plan_path"]
                # Extract S3 key from S3 URL if it's a full URL
                if plan_path.startswith("s3://"):
                    s3_key = plan_path.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                elif plan_path.startswith("repair_plans/"):
                    s3_key = plan_path
                elif "/" in plan_path:
                    s3_key = plan_path
                else:
                    s3_key = f"repair_plans/{plan_path}"
                
                file_exists = s3_service.file_exists(s3_key)
                if file_exists:
                    result["storage"] = True
                else:
                    result["issues"].append(f"Missing in S3: {s3_key}")
            except Exception as e:
                result["issues"].append(f"S3 error: {e}")
        else:
            result["issues"].append("No plan_path in database")
        
        # Check Pinecone
        try:
            pinecone_id = f"{conflict_id}_{partner_id}"
            pinecone_result = pinecone_service.get_by_conflict_id(pinecone_id, namespace="repair_plans")
            if pinecone_result and pinecone_result.metadata:
                result["pinecone"] = True
            else:
                result["issues"].append(f"Missing in Pinecone (repair_plans namespace, ID: {pinecone_id})")
        except Exception as e:
            result["issues"].append(f"Pinecone error: {e}")
        
        return result
    
    def check_profile(self, profile_id: str) -> Dict[str, Any]:
        """Check if profile exists in all 3 places"""
        result = {
            "profile_id": profile_id,
            "type": "profile",
            "database": False,
            "storage": False,
            "pinecone": False,
            "issues": []
        }
        
        # Check database
        try:
            profile = db_service.get_profile_by_id(profile_id)
            if profile:
                result["database"] = True
                result["file_path"] = profile.get("file_path")
                result["pdf_id"] = profile.get("pdf_id")
                result["pdf_type"] = profile.get("pdf_type")
            else:
                result["issues"].append("Missing in database")
        except Exception as e:
            result["issues"].append(f"Database error: {e}")
        
        # Check storage (S3)
        if result.get("file_path"):
            try:
                file_path = result["file_path"]
                # Extract S3 key from S3 URL if it's a full URL
                if file_path.startswith("s3://"):
                    s3_key = file_path.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                elif any(file_path.startswith(f"{folder}/") for folder in ["profiles", "handbooks"]):
                    s3_key = file_path
                elif "/" in file_path:
                    s3_key = file_path
                else:
                    folder = "profiles" if result.get("pdf_type") in ["boyfriend_profile", "girlfriend_profile"] else "handbooks"
                    s3_key = f"{folder}/{file_path}"
                
                file_exists = s3_service.file_exists(s3_key)
                if file_exists:
                    result["storage"] = True
                else:
                    result["issues"].append(f"Missing in S3: {s3_key}")
            except Exception as e:
                result["issues"].append(f"S3 error: {e}")
        else:
            result["issues"].append("No file_path in database")
        
        # Check Pinecone
        if result.get("pdf_id") and result.get("pdf_type"):
            try:
                namespace = "profiles" if result["pdf_type"] in ["boyfriend_profile", "girlfriend_profile"] else "handbooks"
                vector_id = f"{result['pdf_type']}_{result['pdf_id']}"
                fetch_result = pinecone_service.index.fetch(ids=[vector_id], namespace=namespace)
                if fetch_result.vectors and vector_id in fetch_result.vectors:
                    result["pinecone"] = True
                else:
                    result["issues"].append(f"Missing in Pinecone ({namespace} namespace, ID: {vector_id})")
            except Exception as e:
                result["issues"].append(f"Pinecone error: {e}")
        
        return result
    
    def verify_all_conflicts(self, relationship_id: Optional[str] = None):
        """Verify all conflicts"""
        print("🔍 Verifying all conflicts...")
        
        query = self.supabase.table("conflicts").select("id, relationship_id")
        if relationship_id:
            query = query.eq("relationship_id", relationship_id)
        
        conflicts = query.execute()
        
        results = []
        for conflict in conflicts.data:
            conflict_id = conflict["id"]
            print(f"  Checking conflict {conflict_id[:8]}...")
            result = self.check_conflict(conflict_id)
            results.append(result)
            
            # Check analysis
            analysis_result = self.check_analysis(conflict_id)
            results.append(analysis_result)
            
            # Check repair plans
            for partner_id in ["partner_a", "partner_b"]:
                plan_result = self.check_repair_plan(conflict_id, partner_id)
                results.append(plan_result)
        
        return results
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """Print verification summary"""
        print("\n" + "="*80)
        print("VERIFICATION SUMMARY")
        print("="*80)
        
        total = len(results)
        complete = sum(1 for r in results if r.get("database") and r.get("storage") and r.get("pinecone"))
        incomplete = total - complete
        
        print(f"\nTotal items checked: {total}")
        print(f"✅ Complete (all 3 locations): {complete}")
        print(f"⚠️  Incomplete (missing in some locations): {incomplete}")
        
        if incomplete > 0:
            print("\n⚠️  ISSUES FOUND:")
            for result in results:
                if result.get("issues"):
                    print(f"\n  {result.get('type', 'item')} - {result.get('conflict_id', result.get('profile_id', 'unknown'))[:8]}")
                    for issue in result["issues"]:
                        print(f"    - {issue}")
        
        print("\n" + "="*80)


def main():
    parser = argparse.ArgumentParser(description="Verify data integrity across all storage systems")
    parser.add_argument("--conflict-id", help="Check specific conflict ID")
    parser.add_argument("--relationship-id", help="Check all conflicts for relationship")
    parser.add_argument("--profile-id", help="Check specific profile ID")
    
    args = parser.parse_args()
    
    checker = DataIntegrityChecker()
    
    if args.conflict_id:
        print(f"🔍 Checking conflict {args.conflict_id}...")
        results = [
            checker.check_conflict(args.conflict_id),
            checker.check_analysis(args.conflict_id),
            checker.check_repair_plan(args.conflict_id, "partner_a"),
            checker.check_repair_plan(args.conflict_id, "partner_b")
        ]
        checker.print_summary(results)
    elif args.profile_id:
        print(f"🔍 Checking profile {args.profile_id}...")
        result = checker.check_profile(args.profile_id)
        checker.print_summary([result])
    else:
        results = checker.verify_all_conflicts(args.relationship_id)
        checker.print_summary(results)


if __name__ == "__main__":
    main()

