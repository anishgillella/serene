import logging
from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)

class Neo4jService:
    """Service for interacting with Neo4j graph database"""
    
    def __init__(self):
        self.driver = None
        try:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
            )
            logger.info("✅ Connected to Neo4j")
        except Exception as e:
            logger.warning(f"⚠️ Failed to connect to Neo4j: {e}")

    def close(self):
        if self.driver:
            self.driver.close()

    def create_conflict_node(self, conflict_data: Dict[str, Any]):
        """
        Create a Conflict node and link it to Topics and People.
        
        conflict_data should contain:
        - conflict_id
        - summary
        - date
        - root_causes (list of strings)
        - intensity (optional)
        """
        if not self.driver:
            return

        query = """
        MERGE (c:Conflict {id: $conflict_id})
        SET c.summary = $summary,
            c.date = datetime($date),
            c.intensity = $intensity,
            c.created_at = datetime()
            
        WITH c
        UNWIND $root_causes AS topic_name
        MERGE (t:Topic {name: topic_name})
        MERGE (c)-[:ABOUT]->(t)
        """
        
        try:
            with self.driver.session() as session:
                session.run(query, 
                    conflict_id=conflict_data["conflict_id"],
                    summary=conflict_data.get("summary", ""),
                    date=conflict_data.get("date", datetime.now().isoformat()),
                    intensity=conflict_data.get("intensity", 5),
                    root_causes=conflict_data.get("root_causes", [])
                )
                logger.info(f"✅ Created graph nodes for conflict {conflict_data['conflict_id']}")
        except Exception as e:
            logger.error(f"❌ Error creating conflict node in Neo4j: {e}")

    def link_conflicts(self, parent_id: str, child_id: str, relationship_type: str = "EVOLVED_FROM"):
        """Link two conflicts (e.g., Child EVOLVED_FROM Parent)"""
        if not self.driver:
            return

        query = f"""
        MATCH (parent:Conflict {{id: $parent_id}})
        MATCH (child:Conflict {{id: $child_id}})
        MERGE (child)-[:{relationship_type}]->(parent)
        """
        
        try:
            with self.driver.session() as session:
                session.run(query, parent_id=parent_id, child_id=child_id)
                logger.info(f"✅ Linked conflict {child_id} -> {parent_id}")
        except Exception as e:
            logger.error(f"❌ Error linking conflicts in Neo4j: {e}")

    def find_related_conflicts(self, conflict_id: str) -> List[Dict[str, Any]]:
        """
        Find related conflicts via Topic or Saga links.
        Returns a list of related conflicts with the reason for connection.
        """
        if not self.driver:
            return []

        # Query to find:
        # 1. Direct ancestors (Saga)
        # 2. Conflicts sharing the same Topic
        query = """
        MATCH (c:Conflict {id: $conflict_id})
        
        // 1. Find Saga chain (ancestors)
        OPTIONAL MATCH (c)-[:EVOLVED_FROM*]->(ancestor:Conflict)
        
        // 2. Find Topic siblings
        OPTIONAL MATCH (c)-[:ABOUT]->(t:Topic)<-[:ABOUT]-(sibling:Conflict)
        WHERE sibling.id <> c.id
        
        RETURN 
            ancestor.id as ancestor_id, 
            ancestor.summary as ancestor_summary,
            sibling.id as sibling_id,
            sibling.summary as sibling_summary,
            t.name as shared_topic
        LIMIT 10
        """
        
        related = []
        try:
            with self.driver.session() as session:
                result = session.run(query, conflict_id=conflict_id)
                for record in result:
                    if record["ancestor_id"]:
                        related.append({
                            "type": "saga",
                            "id": record["ancestor_id"],
                            "summary": record["ancestor_summary"],
                            "reason": "Direct continuation"
                        })
                    if record["sibling_id"]:
                        related.append({
                            "type": "topic",
                            "id": record["sibling_id"],
                            "summary": record["sibling_summary"],
                            "reason": f"Shared topic: {record['shared_topic']}"
                        })
            
            # Deduplicate
            unique_related = {r["id"]: r for r in related}.values()
            return list(unique_related)
            
        except Exception as e:
            logger.error(f"❌ Error querying Neo4j: {e}")
            return []

# Singleton instance
neo4j_service = Neo4jService()
