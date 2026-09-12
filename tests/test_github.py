from src.scrapers.github import GitHubResolver


def test_extract_github_url():
    text = (
        "Source code is available at "
        "https://github.com/example/research-project"
    )

    url = GitHubResolver.extract_github_url(text)

    assert url == (
        "https://github.com/example/research-project"
    )


def test_extract_github_url_missing():
    text = "No repository is mentioned here."

    url = GitHubResolver.extract_github_url(text)

    assert url is None


def test_tokens():
    tokens = GitHubResolver.tokenize(
        "Attention Is All You Need"
    )

    assert "attention" in tokens
    assert "need" in tokens
    assert "is" not in tokens


def test_confidence_score():
    score = GitHubResolver.confidence_score(
        "Attention Is All You Need",
        "attention-is-all-you-need",
        "Implementation of Attention Is All You Need",
    )

    assert score == 1.0


def test_empty_result():
    result = {
        "github_url": None,
        "github_stars": None,
        "github_confidence": 0.0,
    }

    assert result["github_url"] is None
    assert result["github_stars"] is None
    assert result["github_confidence"] == 0.0