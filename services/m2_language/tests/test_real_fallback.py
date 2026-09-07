from services.m2_language.providers.factory import create_language_provider


def main():
    print("M2 REAL FALLBACK FACTORY TEST")

    provider = create_language_provider()

    print(f"Wrapper: {type(provider).__name__}")
    print(f"Primary: {type(provider.primary).__name__}")
    print(f"Fallback: {type(provider.fallback).__name__}")

    assert type(provider).__name__ == "FallbackLanguageProvider"
    assert type(provider.primary).__name__ == "SarvamProvider"
    assert type(provider.fallback).__name__ == "LocalProvider"

    print("REAL FALLBACK FACTORY TEST PASSED")


if __name__ == "__main__":
    main()