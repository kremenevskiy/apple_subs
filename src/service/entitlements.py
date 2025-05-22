import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Subscription, SubStatus, TxLog, User

CONSUMABLE = {"credits.50": 50, "credits.100": 100}
SUB_BONUS = 100  # credits per renewal


async def grant_entitlements(tx: dict, db: AsyncSession):
    txn_id = tx["transactionId"]
    prod_id = tx["productId"]
    user_id = tx.get("appAccountToken")
    env = tx["environment"]

    # idempotency
    if await db.get(TxLog, txn_id):
        return
    db.add(TxLog(transaction_id=txn_id, raw=str(tx)))

    user = await db.get(User, user_id) or User(id=user_id)
    db.add(user)

    if tx["type"] == "Consumable":
        user.credits += CONSUMABLE.get(prod_id, 0)

    elif tx["type"] == "Auto-Renewable Subscription":
        sub = await db.get(Subscription, tx["originalTransactionId"]) or Subscription(
            original_txn_id=tx["originalTransactionId"], user=user, product_id=prod_id
        )
        sub.status = SubStatus.active
        sub.expires_at = dt.datetime.fromtimestamp(
            tx["expiresDate"] / 1000, dt.timezone.utc
        )
        sub.last_env = env
        user.credits += SUB_BONUS

    await db.commit()


async def revoke_subscription(tx: dict, db: AsyncSession):
    sub = await db.get(Subscription, tx["originalTransactionId"])
    if not sub:
        return
    sub.status = SubStatus.expired
    await db.commit()
