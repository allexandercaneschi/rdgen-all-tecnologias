"""
Builds geradas (ALL Tecnologias).

/builds                      -> painel protegido por senha (BUILDS_PASSWORD) que lista
                                todas as builds guardadas em exe/<uuid>/, com download
                                de cada arquivo e opção de excluir builds.
/builds/<uuid>/<arquivo>     -> download de um arquivo de uma build específica (protegido).
/latest/<arquivo>            -> link PÚBLICO e fixo que sempre entrega a versão mais
                                recente daquele arquivo (ex.: /latest/ALLRemote.exe).
/latest/<atalho>             -> atalhos por tipo: exe, msi, apk, apk-armv7, apk-x86_64,
                                dmg, dmg-intel, deb, rpm, appimage. Entregam o arquivo
                                mais recente daquele tipo, de qualquer build.

Variáveis de ambiente:
  BUILDS_PASSWORD   senha do painel /builds (sem ela o painel fica desativado)
  BUILDS_USER       usuário do painel (padrão: admin)
  LATEST_ENABLED    "false" desativa os links públicos /latest (padrão: true)
"""
import base64
import datetime
import os
import re
import secrets
import shutil
from urllib.parse import urlparse

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

EXE_DIR = os.path.join(str(settings.BASE_DIR), 'exe')

_UUID_RE = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
_NAME_RE = re.compile(r'^[\w.-]+$')

# Horário de Brasília (sem horário de verão desde 2019)
_BRT = datetime.timezone(datetime.timedelta(hours=-3))

# Atalhos de /latest/<atalho>: função que diz se o nome do arquivo combina
_ATALHOS = {
    'exe': lambda n: n.endswith('.exe'),
    'msi': lambda n: n.endswith('.msi'),
    'apk': lambda n: n.endswith('-aarch64.apk'),
    'apk-aarch64': lambda n: n.endswith('-aarch64.apk'),
    'apk-armv7': lambda n: n.endswith('-armv7.apk'),
    'apk-x86_64': lambda n: n.endswith('-x86_64.apk'),
    'dmg': lambda n: n.endswith('-aarch64.dmg'),
    'dmg-intel': lambda n: n.endswith('-x86_64.dmg'),
    'deb': lambda n: n.endswith('-x86_64.deb') and 'wayland' not in n,
    'rpm': lambda n: n.endswith('-x86_64.rpm') and 'suse' not in n,
    'appimage': lambda n: n.endswith('-x86_64.AppImage'),
}

_TIPOS = [
    ('.apk', 'fab fa-android', 'Android'),
    ('.exe', 'fab fa-windows', 'Windows'),
    ('.msi', 'fab fa-windows', 'Windows'),
    ('.dmg', 'fab fa-apple', 'macOS'),
]


# --------------------------------------------------------------------------- auth

def _auth_ok(request):
    senha = os.environ.get('BUILDS_PASSWORD', '')
    if not senha:
        return False
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Basic '):
        return False
    try:
        user, pwd = base64.b64decode(auth[6:]).decode('utf-8').split(':', 1)
    except Exception:
        return False
    usuario = os.environ.get('BUILDS_USER', 'admin')
    return secrets.compare_digest(user, usuario) and secrets.compare_digest(pwd, senha)


def _negar(request):
    if not os.environ.get('BUILDS_PASSWORD', ''):
        return HttpResponseForbidden(
            'Painel de builds desativado: defina a variável BUILDS_PASSWORD no container.')
    r = HttpResponse('Autenticação necessária', status=401)
    r['WWW-Authenticate'] = 'Basic realm="Builds ALL Tecnologias", charset="UTF-8"'
    return r


def _protegido(view):
    def wrapper(request, *args, **kwargs):
        if not _auth_ok(request):
            return _negar(request)
        return view(request, *args, **kwargs)
    wrapper.__name__ = view.__name__
    return wrapper


# ------------------------------------------------------------------------ helpers

def _quando(ts):
    return datetime.datetime.fromtimestamp(ts, tz=_BRT)


def _tipo(nome):
    for ext, icone, rotulo in _TIPOS:
        if nome.endswith(ext):
            return icone, rotulo
    return 'fab fa-linux', 'Linux'


def _todos_arquivos():
    """Lista (uuid, nome, caminho, mtime, tamanho) de tudo que existe em exe/."""
    itens = []
    if not os.path.isdir(EXE_DIR):
        return itens
    for uid in os.listdir(EXE_DIR):
        if not _UUID_RE.match(uid):
            continue
        pasta = os.path.join(EXE_DIR, uid)
        if not os.path.isdir(pasta):
            continue
        for nome in os.listdir(pasta):
            caminho = os.path.join(pasta, nome)
            if nome.startswith('.') or not os.path.isfile(caminho):
                continue
            st = os.stat(caminho)
            itens.append((uid, nome, caminho, st.st_mtime, st.st_size))
    return itens


def _mais_recente(filtro):
    candidatos = [i for i in _todos_arquivos() if filtro(i[1])]
    if not candidatos:
        return None
    return max(candidatos, key=lambda i: i[3])


def _enviar(caminho, nome, cache=True):
    resp = FileResponse(open(caminho, 'rb'), as_attachment=True, filename=nome)
    if nome.endswith('.apk'):
        resp['Content-Type'] = 'application/vnd.android.package-archive'
    if not cache:
        # o link /latest muda de conteúdo a cada build nova; não deixar proxy/navegador guardar
        resp['Cache-Control'] = 'no-store'
    return resp


# -------------------------------------------------------------------------- views

@_protegido
def builds(request):
    itens = _todos_arquivos()

    por_build = {}
    for uid, nome, _caminho, mtime, tamanho in itens:
        b = por_build.setdefault(uid, {'uuid': uid, 'mtime': 0, 'arquivos': []})
        icone, rotulo = _tipo(nome)
        b['arquivos'].append({'nome': nome, 'mb': f'{tamanho / 1048576:.1f}'.replace('.', ','),
                              'icone': icone})
        b['mtime'] = max(b['mtime'], mtime)
        b['plataforma'] = rotulo
        b['icone'] = icone
    lista = sorted(por_build.values(), key=lambda b: b['mtime'], reverse=True)
    for b in lista:
        b['data'] = _quando(b['mtime'])
        b['arquivos'].sort(key=lambda a: a['nome'])

    # Links públicos: o arquivo mais recente de cada nome
    recentes = {}
    for uid, nome, _caminho, mtime, _t in itens:
        if nome not in recentes or mtime > recentes[nome]['mtime']:
            recentes[nome] = {'nome': nome, 'mtime': mtime, 'uuid': uid}
    latest = sorted(recentes.values(), key=lambda r: r['nome'].lower())
    for r in latest:
        r['data'] = _quando(r['mtime'])
        r['icone'] = _tipo(r['nome'])[0]

    atalhos = []
    for chave in ('exe', 'msi', 'apk', 'apk-armv7', 'apk-x86_64', 'dmg', 'dmg-intel', 'deb', 'rpm', 'appimage'):
        alvo = _mais_recente(_ATALHOS[chave])
        if alvo:
            atalhos.append({'chave': chave, 'nome': alvo[1]})

    base = f"{settings.PROTOCOL}://{request.get_host()}"
    return render(request, 'builds.html', {
        'builds': lista,
        'latest': latest,
        'atalhos': atalhos,
        'base_url': base,
        'latest_ativo': os.environ.get('LATEST_ENABLED', 'true').lower() != 'false',
        'msg': request.GET.get('msg', ''),
    })


@_protegido
def builds_baixar(request, uid, nome):
    if not _UUID_RE.match(uid) or not _NAME_RE.match(nome) or nome.startswith('.'):
        raise Http404
    caminho = os.path.join(EXE_DIR, uid, nome)
    if not os.path.isfile(caminho):
        raise Http404
    return _enviar(caminho, nome)


@require_http_methods(['POST'])
@_protegido
def builds_excluir(request, uid):
    if not _UUID_RE.match(uid):
        raise Http404
    # O CSRF do Django está desligado neste projeto e o Basic Auth é enviado
    # automaticamente pelo navegador: só aceita exclusão vinda da própria página.
    origem = request.META.get('HTTP_ORIGIN') or request.META.get('HTTP_REFERER') or ''
    if urlparse(origem).netloc != request.get_host():
        return HttpResponseForbidden('Origem inválida')
    pasta = os.path.join(EXE_DIR, uid)
    if os.path.isdir(pasta):
        shutil.rmtree(pasta)
        return redirect('/builds/?msg=excluida')
    raise Http404


def latest(request, nome):
    """Link público e fixo: sempre a versão mais recente do arquivo pedido."""
    if os.environ.get('LATEST_ENABLED', 'true').lower() == 'false':
        raise Http404
    if not _NAME_RE.match(nome) or nome.startswith('.'):
        raise Http404
    filtro = _ATALHOS.get(nome.lower())
    if filtro is None:
        filtro = lambda n: n == nome
    alvo = _mais_recente(filtro)
    if not alvo:
        raise Http404('Nenhuma build encontrada para este arquivo')
    return _enviar(alvo[2], alvo[1], cache=False)
