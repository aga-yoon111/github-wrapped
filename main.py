import requests
import os
import argparse
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from datetime import datetime, timedelta, timezone

console = Console()
#carregar token
load_dotenv()
GITHUB_TOKEN= os.environ.get("GITHUB_TOKEN")

#verifica se tem github token
if not GITHUB_TOKEN:
    print("[bold red]Erro:[bold red] o GITHUB_TOKEN não foi encontrado!")
    exit()

#criação da sessao
session = requests.Session()
session.headers.update({
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
})

#faz a parte de username e days
parser = argparse.ArgumentParser(description= "Gerador de  GitHub Wrapped")

parser.add_argument("--username", required=True)
parser.add_argument("--days", type=int, required=True)

args = parser.parse_args()

#verifica se número de dias é válido
if args.days <=0:
    print("[bold red]Erro:[bold red] número de dias inválido! Precisa ser um número inteiro positivo maior que 0.")
    exit()



#DATA ATUAL e LIMITE
agora = datetime.now(timezone.utc)
data_limite = agora - timedelta(days=args.days)



#for das páginas

page = 1

events = []

while True:
    parar = False
    link = f"https://api.github.com/users/{args.username}/events?page={page}"
    response = session.get(link)

    if response.status_code !=200:
        print("Erro na requisição:", response.status_code)
        print(response.text)
        break
    if response.status_code == 404:
        raise ValueError("User not found.")
        break


    eventos = response.json()

    if not eventos:
        break


    for ev in eventos:
        data = ev["created_at"]
        data_do_evento = datetime.fromisoformat(data.replace("Z", "+00:00"))
        if(data_do_evento<data_limite):
            parar = True
            break
        else:
            events.append(ev)
    if parar:
        break

    page+=1

#VERIFICACAO
tem_dados = len(events) > 0

if not tem_dados:
    aviso = Panel(
        "✨ [bold white]Parece que você tirou férias![/]\nNão encontramos atividades neste período.",
        style="on blue",
        expand=False
    )
    console.print(aviso)
    exit()

#CALCULANDO COISAS
total_commits = 0
total_prs_opened = 0
total_prs_closed = 0
total_issues_opened = 0

dicio_repos = {}

for evento in events:
    if evento['type']=='PushEvent':
        payload = evento.get('payload', {})
        
        num_commits = payload.get('size', len(payload.get('commits', [0])))

        total_commits+=num_commits

    
    if evento['type']=='PullRequestEvent':
        payload = evento.get('payload', {})

        acao =payload.get('action')

        if acao == 'opened':
            total_prs_opened+=1
        if acao=='closed':
            mergg = payload.get('merged')
            if mergg:
                total_prs_closed+=1


    if evento['type'] == 'IssuesEvent':
        payload = evento.get('payload', {})
        acao =payload.get('action')

        if(acao == 'opened'):
            total_issues_opened+=1
            
#printar pra ver se deu certo
'''
print(f"total commits: {total_commits}")
print(f"total prs opened: {total_prs_opened}")
print(f"total prs closed: {total_prs_closed}")
print(f"total issues opened: {total_issues_opened}")
'''
#TOP 5 REPOSITORIOS

#fazer dicionário e ir adicionando {repositorio_nome : total commits}
for evento in events:
    repo = evento.get('repo', {})
    nome_repo = repo.get('name')
    if nome_repo not in dicio_repos:
        dicio_repos[nome_repo] = 0

for evento in events:
    payloadd = evento.get('payload', {})
        
    nume_commits = payloadd.get('size', len(payloadd.get('commits', [0])))
    repos = evento.get('repo', {})
    nome_repos = repos.get('name')

    dicio_repos[nome_repos]+=nume_commits

#print(dicio_repos)

#ordenando dicionário de forma decrescente

dicio_ordenado = dict(sorted(dicio_repos.items(), key=lambda item: item[1], reverse=True))


#DIA MAIS MOVIMENTADO

dicio_datas = {}
#fazer dicionario e ir adicionando {data : total de eventos}
for evento in events:
    data_completa = evento["created_at"]
    data_curta = data_completa[:10]
    if data_curta not in dicio_datas:
        dicio_datas[data_curta]=0
    
for evento in events:
    data_comp = evento["created_at"]
    data_curt = data_comp[:10]
    dicio_datas[data_curt]+=1

#print(dicio_datas)

#achar dia mais movimentado

dicio_orden = dict(sorted(dicio_datas.items(), key=lambda item: item[1], reverse=True))
#print(dicio_orden)

#USO DAS LINGUAGENS
#dicionario de linguagens

repos_usados = set()
for evento in events:
    repo = evento.get('repo', {})
    nome = repo.get('name')
    if nome:
        repos_usados.add(nome)

dicio_lan = {}
dicio_lan["Python"] = 0
dicio_lan["JavaScript"] = 0
dicio_lan["C#"] = 0
dicio_lan["TypeScript"] = 0
dicio_lan["Java"] = 0
dicio_lan["Outros"] = 0

for nome_repo in repos_usados:
    linkk = f"https://api.github.com/repos/{nome_repo}"
    resposta = session.get(linkk)

    if resposta.status_code !=200:
        continue

    dados = resposta.json()

    linguagem = dados['language']
    if linguagem == "Python":
        dicio_lan["Python"]+=1
    elif linguagem == "JavaScript":
        dicio_lan["JavaScript"]+=1
    elif linguagem == "C#":
        dicio_lan["C#"]+=1
    elif linguagem == "TypeScript":
        dicio_lan["TypeScript"]+=1
    elif linguagem == "Java":
        dicio_lan["Java"]+=1
    else:
        dicio_lan["Outros"]+=1

dicio_lan_ord = dict(sorted(dicio_lan.items(), key=lambda item: item[1], reverse=True))




console.print(f"[bold green]GitHub Activity Report for: {args.username} (last {args.days} days)")

chaves = list(dicio_orden)

resumo = f"Total Commits: {total_commits}\nPull Requests Opened: {total_prs_opened}\nPull Requests Merged: {total_prs_closed}\nIssues Opened: {total_issues_opened}\n\n[bold yellow]--- Busiest Day ---[/]\n{chaves[0]}: {dicio_orden[chaves[0]]} events"
meu_painel = Panel(resumo, title="[bold cyan]Summary Github Wrapped")
console.print(meu_painel)

#TOP 5

chave = list(dicio_ordenado)
tabela = Table(title = "[bold cyan]Top 5 Repositories (by commit count)")

tabela.add_column("Rank", style = "dim", width=6)
tabela.add_column("Repository", style = "cyan")
tabela.add_column("Commits", justify="right")

tabela.add_row(f"1. ", chave[0], str(dicio_ordenado[chave[0]]))
tabela.add_row(f"2. ", chave[1], str(dicio_ordenado[chave[1]]))
tabela.add_row(f"3. ", chave[2], str(dicio_ordenado[chave[2]]))
tabela.add_row(f"4. ", chave[3], str(dicio_ordenado[chave[3]]))
tabela.add_row(f"5. ", chave[4], str(dicio_ordenado[chave[4]]))

console.print(tabela)

#LANGUAGES
chavec = list(dicio_lan_ord)
console.print("\n[bold cyan]--- Use of Languages ---[/]")
console.print(f"• [yellow]{chavec[0]}: {dicio_lan_ord[chavec[0]]}[/]")
console.print(f"• [blue]{chavec[1]}: {dicio_lan_ord[chavec[1]]}[/]")
console.print(f"• [orange]{chavec[2]}: {dicio_lan_ord[chavec[2]]}[/]")
console.print(f"• [green]{chavec[3]}: {dicio_lan_ord[chavec[3]]}[/]")
console.print(f"• [purple]{chavec[4]}: {dicio_lan_ord[chavec[4]]}[/]")


















