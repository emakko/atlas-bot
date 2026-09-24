async def test_subscribe_update_and_unsubscribe(storage):
    assert await storage.subscribe(1, 100, "se", None) is True
    assert await storage.subscribe(1, 100, "se", 7) is False
    subs = await storage.subscriptions(guild_id=1)
    assert len(subs) == 1 and subs[0].role_id == 7

    await storage.subscribe(1, 101, "paluno", None)
    assert await storage.subscribed_source_keys() == {"se", "paluno"}

    assert await storage.unsubscribe(100, "se") is True
    assert await storage.unsubscribe(100, "se") is False
    await storage.remove_channel(101)
    assert await storage.subscriptions() == []


async def test_seen_tracking(storage):
    assert not await storage.is_primed("se")
    await storage.mark_seen("se", ["a", "b"], prime=True)
    assert await storage.is_primed("se")
    assert await storage.unseen("se", ["a", "c"]) == {"c"}
    assert await storage.unseen("other", ["a"]) == {"a"}
    assert await storage.unseen("se", []) == set()
