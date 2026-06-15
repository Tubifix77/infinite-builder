def test_import():
    from builder.keychain import Keychain
    from builder.journal import Journal
    assert True

def test_keychain_init():
    from builder.keychain import Keychain
    kc = Keychain()
    providers = kc.available_providers()
    assert isinstance(providers, list)
