import pytest

from app.services.repo_url import parse_github_url


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://github.com/owner/repo", ("owner", "repo")),
        ("https://github.com/owner/repo.git", ("owner", "repo")),
        ("https://github.com/owner/repo/", ("owner", "repo")),
        ("https://github.com/owner/repo.git/", ("owner", "repo")),
        ("https://github.com/my-org/my_repo.name", ("my-org", "my_repo.name")),
    ],
)
def test_parse_github_url_valid(url, expected):
    assert parse_github_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/owner/repo",  # non-https scheme
        "https://gitlab.com/owner/repo",  # non-allowed host
        "https://evil.com/github.com/owner/repo",  # host not in allowlist
        "https://user@github.com/owner/repo",  # credentials in URL
        "https://github.com/owner/repo/extra",  # extra path segment
        "https://github.com/owner",  # missing name segment
        "https://github.com/owner/repo?foo=bar",  # query string
        "https://github.com/owner/repo#fragment",  # fragment
        "https://github.com/ow ner/repo",  # bad chars in owner
        "https://github.com/owner/re;po",  # bad chars in name
        "ftp://github.com/owner/repo",  # non-https scheme
    ],
)
def test_parse_github_url_rejected(url):
    with pytest.raises(ValueError):
        parse_github_url(url)
