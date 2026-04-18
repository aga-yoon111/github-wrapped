import requests
import os
import argparse
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from datetime import datetime, timedelta, timezone
from collections import Counter

console = Console()

def criar_sessao():
    load_dotenv()
    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        console.print("[bold red]Erro:[/] GITHUB_TOKEN não encontrado no .env")
        exit()

    session = requests.Session()
    session.headers.update({
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    })
    return session


def tratar_erros(response):
    if response.status_code == 404:
        console.print("[bold red]Erro:[/] Usuário não encontrado.")
        exit()
    elif response.status_code in [401, 403]:
        console.print("[bold red]Erro:[/] Falha de autenticação ou limite da API excedido.")
        exit()
    elif response.status_code >= 500:
        console.print("[bold red]Erro:[/] Problema no servidor do GitHub.")
        exit()
    elif response.status_code != 200:
        console.print(f"[bold red]Erro inesperado:[/] {response.status_code}")
        exit()


# ✅ NOVO: tratamento de erro de rede
def fazer_request(session, url):
    try:
        response = session.get(url, timeout=10)
        tratar_erros(response)
        return response
    except requests.exceptions.RequestException:
        console.print("[bold red]Erro de rede:[/] Falha ao conectar com a API do GitHub.")
        exit()


def buscar_eventos(session, username, dias):
    agora = datetime.now(timezone.utc)
    limite = agora - timedelta(days=dias)

    eventos_filtrados = []
    page = 1

    while True:
        url = f"https://api.github.com/users/{username}/events?per_page=100&page={page}"
        response = fazer_request(session, url)

        eventos = response.json()
        if not eventos:
            break

        parar = False

        for ev in eventos:
            data = datetime.fromisoformat(ev["created_at"].replace("Z", "+00:00"))

            if data < limite:
                parar = True
                break

            eventos_filtrados.append(ev)

        if parar:
            break

        page += 1

    return eventos_filtrados


def buscar_repos(session, username):
    repos = []
    page = 1

    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        response = fazer_request(session, url)

        dados = response.json()
        if not dados:
            break

        repos.extend(dados)
        page += 1

    return repos


def calcular_estatisticas(events):
    total_commits = 0
    prs_opened = 0
    prs_merged = 0
    issues_opened = 0

    repos_counter = Counter()
    dias_counter = Counter()

    for ev in events:
        tipo = ev["type"]
        payload = ev.get("payload", {})

        # commits
        if tipo == "PushEvent":
            total_commits += payload.get("size", 0)

        # PRs
        if tipo == "PullRequestEvent":
            if payload.get("action") == "opened":
                prs_opened += 1
            if payload.get("action") == "closed" and payload.get("pull_request", {}).get("merged"):
                prs_merged += 1

        # issues
        if tipo == "IssuesEvent" and payload.get("action") == "opened":
            issues_opened += 1

        # TOP REPOS (frequência de eventos)
        repo_nome = ev.get("repo", {}).get("name")
        if repo_nome:
            repos_counter[repo_nome] += 1

        # dias
        dia = ev["created_at"][:10]
        dias_counter[dia] += 1

    return {
        "commits": total_commits,
        "prs_opened": prs_opened,
        "prs_merged": prs_merged,
        "issues": issues_opened,
        "top_repos": repos_counter.most_common(5),
        "busiest_day": dias_counter.most_common(1)[0] if dias_counter else None
    }


def calcular_linguagens(repos):
    contador = Counter()

    for repo in repos:
        lang = repo.get("language")
        if lang:
            contador[lang] += 1

    return contador.most_common()


def renderizar(username, dias, stats, linguagens):
    console.print(f"\n[bold green]GitHub Activity Report for: {username} (last {dias} days)[/]\n")

    # ✅ estado vazio mais robusto (considera qualquer atividade)
    if not stats["top_repos"]:
        console.print(Panel(
            "✨ [bold white]Sem atividade nesse período![/]",
            style="blue"
        ))
        return

    resumo = (
        f"Total Commits: {stats['commits']}\n"
        f"Pull Requests Opened: {stats['prs_opened']}\n"
        f"Pull Requests Merged: {stats['prs_merged']}\n"
        f"Issues Opened: {stats['issues']}\n\n"
    )

    if stats["busiest_day"]:
        dia, qtd = stats["busiest_day"]
        resumo += f"[bold yellow]Busiest Day:[/]\n{dia}: {qtd} events"

    console.print(Panel(resumo, title="Summary"))

    # TOP 5
    tabela = Table(title="Top 5 Repositories (by activity)")
    tabela.add_column("Rank")
    tabela.add_column("Repo")
    tabela.add_column("Events")

    for i, (repo, qtd) in enumerate(stats["top_repos"], start=1):
        tabela.add_row(str(i), repo, str(qtd))

    console.print(tabela)

    # Linguagens
    console.print("\n[bold cyan]Languages:[/]")
    for lang, qtd in linguagens[:5]:
        console.print(f"• {lang}: {qtd}")


def main():
    parser = argparse.ArgumentParser(description="GitHub Wrapped")
    parser.add_argument("--username", required=True)
    parser.add_argument("--days", type=int, required=True)

    args = parser.parse_args()

    if args.days <= 0:
        console.print("[bold red]Erro:[/] --days deve ser positivo")
        exit()

    session = criar_sessao()

    events = buscar_eventos(session, args.username, args.days)

    if not events:
        console.print(Panel("Sem atividade nesse período.", style="blue"))
        return

    repos = buscar_repos(session, args.username)

    stats = calcular_estatisticas(events)
    linguagens = calcular_linguagens(repos)

    renderizar(args.username, args.days, stats, linguagens)


if __name__ == "__main__":
    main()

