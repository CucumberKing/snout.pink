import pytest
from httpx import AsyncClient

from models import Subscription, User


@pytest.mark.asyncio
async def test_list_subscriptions_empty(authenticated_client: AsyncClient, test_db):
    """Test list subscriptions when none exist."""
    response = await authenticated_client.get("/subscriptions")
    assert response.status_code == 200

    data = response.json()
    assert data["subscriptions"] == []
    assert data["total"] == 0
    assert data["monthly_total"] == 0
    assert data["yearly_total"] == 0


@pytest.mark.asyncio
async def test_list_subscriptions_unauthenticated(client: AsyncClient, test_db):
    """Test list subscriptions without authentication."""
    response = await client.get("/subscriptions")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_subscription(
    authenticated_client: AsyncClient, test_user: User, test_db
):
    """Test create subscription endpoint."""
    subscription_data = {
        "name": "Netflix",
        "price": 15.99,
        "currency": "EUR",
        "cycle": "Monthly",
        "url": "https://netflix.com",
        "color": "rose",
    }

    response = await authenticated_client.post("/subscriptions", json=subscription_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Netflix"
    assert data["price"] == 15.99
    assert data["currency"] == "EUR"
    assert data["cycle"] == "Monthly"
    assert data["url"] == "https://netflix.com"
    assert data["color"] == "rose"
    assert data["user_id"] == test_user.user_id
    assert "subscription_id" in data
    assert "created_ts" in data
    assert "updated_ts" in data


@pytest.mark.asyncio
async def test_create_subscription_minimal(
    authenticated_client: AsyncClient, test_user: User, test_db
):
    """Test create subscription with minimal required fields."""
    subscription_data = {
        "name": "Spotify",
        "price": 9.99,
        "currency": "EUR",
        "cycle": "Monthly",
        "color": "green",
    }

    response = await authenticated_client.post("/subscriptions", json=subscription_data)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Spotify"
    assert data["url"] is None


@pytest.mark.asyncio
async def test_create_subscription_invalid_cycle(
    authenticated_client: AsyncClient, test_db
):
    """Test create subscription with invalid billing cycle."""
    subscription_data = {
        "name": "Test",
        "price": 10.0,
        "currency": "EUR",
        "cycle": "Daily",  # Invalid
        "color": "blue",
    }

    response = await authenticated_client.post("/subscriptions", json=subscription_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_subscription_invalid_color(
    authenticated_client: AsyncClient, test_db
):
    """Test create subscription with invalid color."""
    subscription_data = {
        "name": "Test",
        "price": 10.0,
        "currency": "EUR",
        "cycle": "Monthly",
        "color": "rainbow",  # Invalid
    }

    response = await authenticated_client.post("/subscriptions", json=subscription_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_subscription(
    authenticated_client: AsyncClient, test_user: User, test_db
):
    """Test get single subscription."""
    # Create a subscription first
    subscription = Subscription(
        user_id=test_user.user_id,
        name="Disney+",
        price=8.99,
        currency="EUR",
        cycle="Monthly",
        color="blue",
    )
    await subscription.insert()

    response = await authenticated_client.get(
        f"/subscriptions/{subscription.subscription_id}"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["subscription_id"] == subscription.subscription_id
    assert data["name"] == "Disney+"


@pytest.mark.asyncio
async def test_get_subscription_not_found(authenticated_client: AsyncClient, test_db):
    """Test get subscription that doesn't exist."""
    response = await authenticated_client.get("/subscriptions/nonexistent123")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_subscription_wrong_user(authenticated_client: AsyncClient, test_db):
    """Test that user cannot access another user's subscription."""
    # Create subscription for a different user
    other_user = User(display_name="Other User")
    await other_user.insert()

    subscription = Subscription(
        user_id=other_user.user_id,
        name="Other User Sub",
        price=5.0,
        currency="EUR",
        cycle="Monthly",
        color="purple",
    )
    await subscription.insert()

    response = await authenticated_client.get(
        f"/subscriptions/{subscription.subscription_id}"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_subscription(
    authenticated_client: AsyncClient, test_user: User, test_db
):
    """Test update subscription."""
    subscription = Subscription(
        user_id=test_user.user_id,
        name="Old Name",
        price=10.0,
        currency="EUR",
        cycle="Monthly",
        color="blue",
    )
    await subscription.insert()

    response = await authenticated_client.patch(
        f"/subscriptions/{subscription.subscription_id}",
        json={"name": "New Name", "price": 15.0},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "New Name"
    assert data["price"] == 15.0
    # Unchanged fields should stay the same
    assert data["cycle"] == "Monthly"
    assert data["color"] == "blue"


@pytest.mark.asyncio
async def test_update_subscription_cycle(
    authenticated_client: AsyncClient, test_user: User, test_db
):
    """Test update subscription billing cycle."""
    subscription = Subscription(
        user_id=test_user.user_id,
        name="Annual Sub",
        price=99.0,
        currency="EUR",
        cycle="Monthly",
        color="green",
    )
    await subscription.insert()

    response = await authenticated_client.patch(
        f"/subscriptions/{subscription.subscription_id}",
        json={"cycle": "Yearly"},
    )
    assert response.status_code == 200
    assert response.json()["cycle"] == "Yearly"


@pytest.mark.asyncio
async def test_delete_subscription(
    authenticated_client: AsyncClient, test_user: User, test_db
):
    """Test delete subscription."""
    subscription = Subscription(
        user_id=test_user.user_id,
        name="To Delete",
        price=5.0,
        currency="EUR",
        cycle="Monthly",
        color="slate",
    )
    await subscription.insert()
    sub_id = subscription.subscription_id

    response = await authenticated_client.delete(f"/subscriptions/{sub_id}")
    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()

    # Verify it's actually deleted
    deleted_sub = await Subscription.find_one(Subscription.subscription_id == sub_id)
    assert deleted_sub is None


@pytest.mark.asyncio
async def test_delete_subscription_not_found(
    authenticated_client: AsyncClient, test_db
):
    """Test delete subscription that doesn't exist."""
    response = await authenticated_client.delete("/subscriptions/nonexistent123")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_subscriptions_with_totals(
    authenticated_client: AsyncClient, test_user: User, test_db
):
    """Test list subscriptions returns correct totals."""
    # Create some subscriptions
    subs = [
        Subscription(
            user_id=test_user.user_id,
            name="Monthly Sub",
            price=10.0,
            currency="EUR",
            cycle="Monthly",
            color="blue",
        ),
        Subscription(
            user_id=test_user.user_id,
            name="Yearly Sub",
            price=120.0,  # = 10/month
            currency="EUR",
            cycle="Yearly",
            color="green",
        ),
        Subscription(
            user_id=test_user.user_id,
            name="Weekly Sub",
            price=5.0,  # = ~21.65/month
            currency="EUR",
            cycle="Weekly",
            color="orange",
        ),
    ]

    for sub in subs:
        await sub.insert()

    response = await authenticated_client.get("/subscriptions")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 3

    # Monthly: 10 + 10 + 21.65 = 41.65
    assert abs(data["monthly_total"] - 41.65) < 0.01

    # Yearly: 120 + 120 + 260 = 500
    assert abs(data["yearly_total"] - 500) < 1


@pytest.mark.asyncio
async def test_import_subscriptions(
    authenticated_client: AsyncClient, test_user: User, test_db
):
    """Test import subscriptions."""
    import_data = {
        "subscriptions": [
            {
                "name": "Import 1",
                "price": 10.0,
                "currency": "EUR",
                "cycle": "Monthly",
                "color": "blue",
            },
            {
                "name": "Import 2",
                "price": 20.0,
                "currency": "EUR",
                "cycle": "Yearly",
                "color": "green",
            },
        ],
        "replace": False,
    }

    response = await authenticated_client.post(
        "/subscriptions/import", json=import_data
    )
    assert response.status_code == 200

    data = response.json()
    assert data["imported"] == 2

    # Verify in database
    subs = await Subscription.find(Subscription.user_id == test_user.user_id).to_list()
    assert len(subs) == 2


@pytest.mark.asyncio
async def test_import_subscriptions_replace(
    authenticated_client: AsyncClient, test_user: User, test_db
):
    """Test import subscriptions with replace=True."""
    # Create existing subscription
    existing = Subscription(
        user_id=test_user.user_id,
        name="Existing",
        price=5.0,
        currency="EUR",
        cycle="Monthly",
        color="slate",
    )
    await existing.insert()

    import_data = {
        "subscriptions": [
            {
                "name": "Replacement",
                "price": 15.0,
                "currency": "EUR",
                "cycle": "Monthly",
                "color": "purple",
            },
        ],
        "replace": True,
    }

    response = await authenticated_client.post(
        "/subscriptions/import", json=import_data
    )
    assert response.status_code == 200

    # Verify existing was deleted and new one was created
    subs = await Subscription.find(Subscription.user_id == test_user.user_id).to_list()
    assert len(subs) == 1
    assert subs[0].name == "Replacement"


@pytest.mark.asyncio
async def test_export_subscriptions(
    authenticated_client: AsyncClient, test_user: User, test_db
):
    """Test export subscriptions."""
    # Create some subscriptions
    sub = Subscription(
        user_id=test_user.user_id,
        name="Export Test",
        price=10.0,
        currency="EUR",
        cycle="Monthly",
        color="teal",
    )
    await sub.insert()

    response = await authenticated_client.get("/subscriptions/export/data")
    assert response.status_code == 200

    data = response.json()
    assert data["version"] == 1
    assert "exported_ts" in data
    assert len(data["subscriptions"]) == 1
    assert data["subscriptions"][0]["name"] == "Export Test"
