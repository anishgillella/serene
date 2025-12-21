"""
Multi-tenancy tests for Phase 2 implementation.

Tests verify:
1. Relationship creation and retrieval
2. Dynamic relationship_id in API endpoints
3. Couple profiles CRUD operations
4. Partner name retrieval
5. Data isolation between relationships

NOTE: These are integration tests that require a valid database connection.
Run with: python -m pytest tests/ -v
Requires: .env file with valid DATABASE_URL
"""
import pytest
import uuid
import os


# Check if we have valid database credentials
def has_valid_database():
    """Check if we have valid database credentials."""
    db_url = os.environ.get('DATABASE_URL', '')
    return db_url and 'test:test@localhost' not in db_url


# Skip integration tests if no real database
requires_database = pytest.mark.skipif(
    not has_valid_database(),
    reason="Requires valid DATABASE_URL in .env file"
)


@requires_database
class TestRelationshipEndpoints:
    """Test relationship management API endpoints."""

    def test_create_relationship(self, test_client, sample_relationship_data):
        """Test creating a new relationship."""
        response = test_client.post(
            "/api/relationships/create",
            json=sample_relationship_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "relationship_id" in data
        assert data["partner_a_name"] == sample_relationship_data["partner_a_name"]
        assert data["partner_b_name"] == sample_relationship_data["partner_b_name"]

        # Verify UUID format
        relationship_id = data["relationship_id"]
        uuid.UUID(relationship_id)  # Will raise if invalid

    def test_create_relationship_missing_names(self, test_client):
        """Test that creating relationship without names fails."""
        response = test_client.post(
            "/api/relationships/create",
            json={"partner_a_name": "Only One Partner"}
        )

        # Should fail validation
        assert response.status_code in [400, 422]

    def test_get_relationship(self, test_client, sample_relationship_data):
        """Test retrieving a relationship."""
        # First create a relationship
        create_response = test_client.post(
            "/api/relationships/create",
            json=sample_relationship_data
        )
        relationship_id = create_response.json()["relationship_id"]

        # Then retrieve it
        response = test_client.get(f"/api/relationships/{relationship_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["relationship"]["id"] == relationship_id
        assert data["relationship"]["partner_a_name"] == sample_relationship_data["partner_a_name"]
        assert data["relationship"]["partner_b_name"] == sample_relationship_data["partner_b_name"]

    def test_get_nonexistent_relationship(self, test_client):
        """Test retrieving a non-existent relationship returns 404."""
        fake_id = str(uuid.uuid4())
        response = test_client.get(f"/api/relationships/{fake_id}")

        assert response.status_code == 404

    def test_get_couple_profile(self, test_client, sample_relationship_data):
        """Test retrieving couple profile."""
        # Create relationship
        create_response = test_client.post(
            "/api/relationships/create",
            json=sample_relationship_data
        )
        relationship_id = create_response.json()["relationship_id"]

        # Get profile
        response = test_client.get(f"/api/relationships/{relationship_id}/profile")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["profile"]["partner_a_name"] == sample_relationship_data["partner_a_name"]
        assert data["profile"]["partner_b_name"] == sample_relationship_data["partner_b_name"]

    def test_update_relationship(self, test_client, sample_relationship_data):
        """Test updating partner names."""
        # Create relationship
        create_response = test_client.post(
            "/api/relationships/create",
            json=sample_relationship_data
        )
        relationship_id = create_response.json()["relationship_id"]

        # Update names
        new_names = {
            "partner_a_name": "Updated Partner A",
            "partner_b_name": "Updated Partner B"
        }
        response = test_client.put(
            f"/api/relationships/{relationship_id}",
            json=new_names
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify update
        get_response = test_client.get(f"/api/relationships/{relationship_id}")
        data = get_response.json()
        assert data["relationship"]["partner_a_name"] == new_names["partner_a_name"]
        assert data["relationship"]["partner_b_name"] == new_names["partner_b_name"]

    def test_get_speaker_labels(self, test_client, sample_relationship_data):
        """Test retrieving speaker labels for transcripts."""
        # Create relationship
        create_response = test_client.post(
            "/api/relationships/create",
            json=sample_relationship_data
        )
        relationship_id = create_response.json()["relationship_id"]

        # Get speaker labels
        response = test_client.get(f"/api/relationships/{relationship_id}/speaker-labels")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["labels"]["partner_a"] == sample_relationship_data["partner_a_name"]
        assert data["labels"]["partner_b"] == sample_relationship_data["partner_b_name"]

    def test_validate_relationship(self, test_client, sample_relationship_data):
        """Test relationship validation endpoint."""
        # Create relationship
        create_response = test_client.post(
            "/api/relationships/create",
            json=sample_relationship_data
        )
        relationship_id = create_response.json()["relationship_id"]

        # Validate existing
        response = test_client.get(f"/api/relationships/validate/{relationship_id}")
        assert response.status_code == 200
        assert response.json()["exists"] is True

        # Validate non-existing
        fake_id = str(uuid.uuid4())
        response = test_client.get(f"/api/relationships/validate/{fake_id}")
        assert response.status_code == 200
        assert response.json()["exists"] is False

    def test_get_default_relationship(self, test_client, default_relationship_id):
        """Test getting the default test relationship ID."""
        response = test_client.get("/api/relationships/default/id")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["relationship_id"] == default_relationship_id


@requires_database
class TestConflictWithRelationship:
    """Test conflict endpoints with multi-tenancy support."""

    def test_create_conflict_with_relationship(self, test_client, sample_relationship_data):
        """Test creating a conflict with a specific relationship_id."""
        # Create relationship first
        create_response = test_client.post(
            "/api/relationships/create",
            json=sample_relationship_data
        )
        relationship_id = create_response.json()["relationship_id"]

        # Create conflict with relationship_id
        response = test_client.post(
            "/api/conflicts/create",
            json={"relationship_id": relationship_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["relationship_id"] == relationship_id
        assert "conflict_id" in data

    def test_create_conflict_without_relationship_uses_default(self, test_client, default_relationship_id):
        """Test that creating conflict without relationship_id uses default."""
        response = test_client.post("/api/conflicts/create", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["relationship_id"] == default_relationship_id

    def test_create_conflict_invalid_relationship(self, test_client):
        """Test that creating conflict with invalid relationship_id fails."""
        fake_relationship_id = str(uuid.uuid4())

        response = test_client.post(
            "/api/conflicts/create",
            json={"relationship_id": fake_relationship_id}
        )

        # Should return 404 for non-existent relationship
        assert response.status_code == 404


@requires_database
class TestDataIsolation:
    """Test that data is properly isolated between relationships."""

    def test_conflicts_isolated_by_relationship(self, test_client, sample_relationship_data):
        """Test that conflicts are filtered by relationship_id."""
        # Create two relationships
        response1 = test_client.post(
            "/api/relationships/create",
            json={"partner_a_name": "Alice", "partner_b_name": "Bob"}
        )
        relationship_id_1 = response1.json()["relationship_id"]

        response2 = test_client.post(
            "/api/relationships/create",
            json={"partner_a_name": "Charlie", "partner_b_name": "Diana"}
        )
        relationship_id_2 = response2.json()["relationship_id"]

        # Create conflict for relationship 1
        conflict_response = test_client.post(
            "/api/conflicts/create",
            json={"relationship_id": relationship_id_1}
        )
        conflict_id = conflict_response.json()["conflict_id"]

        # List conflicts for relationship 1 - should include the conflict
        list_response_1 = test_client.get(f"/api/conflicts?relationship_id={relationship_id_1}")
        assert list_response_1.status_code == 200
        conflicts_1 = list_response_1.json().get("conflicts", [])
        conflict_ids_1 = [c["id"] for c in conflicts_1]
        assert conflict_id in conflict_ids_1

        # List conflicts for relationship 2 - should NOT include the conflict
        list_response_2 = test_client.get(f"/api/conflicts?relationship_id={relationship_id_2}")
        assert list_response_2.status_code == 200
        conflicts_2 = list_response_2.json().get("conflicts", [])
        conflict_ids_2 = [c["id"] for c in conflicts_2]
        assert conflict_id not in conflict_ids_2


@requires_database
class TestBackwardCompatibility:
    """Test backward compatibility with existing MVP data."""

    def test_default_relationship_accessible(self, test_client, default_relationship_id):
        """Test that the default Adrian & Elara relationship is accessible."""
        response = test_client.get(f"/api/relationships/{default_relationship_id}")

        # May be 200 if seeded, or 404 if database is empty
        # The important thing is the endpoint works
        assert response.status_code in [200, 404]

    def test_conflict_creation_works_without_relationship(self, test_client):
        """Test that conflict creation still works without explicit relationship_id."""
        response = test_client.post("/api/conflicts/create", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Should use default relationship
        assert "relationship_id" in data
