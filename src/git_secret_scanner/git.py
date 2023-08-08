from __future__ import annotations

import enum

import subprocess
from github import Github
from gitlab import Gitlab


class RepositoryVisibility(enum.StrEnum):
    All = 'all'
    Private = 'private'
    Public = 'public'


class GitResource():
    def __init__(self,
        organization: str,
        visibility: RepositoryVisibility,
        include_archived: bool,
        token = '',
    ):
        self.organization = organization
        self.visibility = visibility
        self.include_archived = include_archived
        self._token = token

    @staticmethod
    def clone(url: str, directory: str) -> None:
        proc = subprocess.run([
                'git', 'clone', '--quiet', url, directory
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        if proc.returncode != 0:
            error = RuntimeError(f'failed to clone repository {url}')
            error.add_note(proc.stderr.decode('utf-8'))
            raise error

    def get_repository_urls(self) -> list[str]:
        raise NotImplementedError('"get_repository_urls" method not implemented')


class GithubResource(GitResource):
    def get_repository_urls(self) -> list[str]:
        github = Github(self._token)

        repository_urls: list[str] = []
        for repo in github.get_organization(self.organization).get_repos(self.visibility):
            if self.include_archived or not repo.archived:
                repository_urls.append(repo.ssh_url)

        return repository_urls


class GitlabResource(GitResource):
    def get_repository_urls(self) -> list[str]:
        visibility = None if self.visibility == RepositoryVisibility.All else self.visibility

        # authenticate user and get the group to analyze
        gitlab = Gitlab(private_token=self._token)
        group = gitlab.groups.get(self.organization)

        repository_urls: list[str] = []

        # get all projects of group
        for repo in group.projects.list(get_all=True, visibility=visibility):
            repository_urls.append(repo.ssh_url_to_repo)

        # remove archived repositories if specified by user
        if not self.include_archived:
            tmp: list[str] = []
            for repo in group.projects.list(get_all=True, archived=True, visibility=visibility):
                tmp.append(repo.ssh_url_to_repo)
            repository_urls = [x for x in repository_urls if x not in [y for y in tmp]]

        return repository_urls
