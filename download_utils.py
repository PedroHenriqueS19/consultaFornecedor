import os
import re
import requests
import xml.etree.ElementTree as ET
from logger_setup import log

HEADERS_BASE = {"User-Agent": "Mozilla/5.0 (compatible; ProspeccaoEduBot/1.0)"}

# Credenciais públicas do Nextcloud da Receita
RFB_WEBDAV_URL = "https://arquivos.receitafederal.gov.br/public.php/webdav/Dados/Cadastros/CNPJ/"
RFB_AUTH = ("gn672Ad4CF8N6TK", "")

def descobrir_pasta_e_arquivos_rfb() -> tuple[str, list]:
    """Usa o protocolo WebDAV para listar os arquivos do Nextcloud da Receita Federal"""
    log.info("Acessando nuvem da Receita Federal para localizar a base mais recente...")
    
    # 1. Busca as pastas mensais disponíveis
    resp = requests.request("PROPFIND", RFB_WEBDAV_URL, auth=RFB_AUTH, headers={"Depth": "1"})
    resp.raise_for_status()
    
    root = ET.fromstring(resp.text)
    pastas = []
    # O namespace do WebDAV
    ns = {'d': 'DAV:'}
    for response in root.findall('d:response', ns):
        href = response.find('d:href', ns).text
        # Procura pastas no formato YYYY-MM
        match = re.search(r'(\d{4}-\d{2})/?$', href)
        if match:
            pastas.append(match.group(1))
            
    if not pastas:
        raise RuntimeError("Não foi possível encontrar as pastas mensais na nuvem da RFB.")
        
    pasta_mais_recente = sorted(pastas)[-1]
    log.info(f"Pasta mensal mais recente identificada: {pasta_mais_recente}")
    
    # 2. Busca os arquivos .zip dentro dessa pasta
    url_pasta = f"{RFB_WEBDAV_URL}{pasta_mais_recente}/"
    resp_arquivos = requests.request("PROPFIND", url_pasta, auth=RFB_AUTH, headers={"Depth": "1"})
    resp_arquivos.raise_for_status()
    
    root_arq = ET.fromstring(resp_arquivos.text)
    arquivos_zip = []
    for response in root_arq.findall('d:response', ns):
        href = response.find('d:href', ns).text
        nome_arquivo = href.split('/')[-1]
        if nome_arquivo.upper().endswith(".ZIP"):
            arquivos_zip.append(nome_arquivo)
            
    return url_pasta, arquivos_zip

def baixar_arquivo_resumivel(url: str, destino: str, tentativas: int = 3) -> None:
    for tentativa in range(1, tentativas + 1):
        try:
            head = requests.head(url, headers=HEADERS_BASE, auth=RFB_AUTH, timeout=60, allow_redirects=True)
            tamanho_total = int(head.headers.get("Content-Length", 0))
            tamanho_local = os.path.getsize(destino) if os.path.exists(destino) else 0

            if tamanho_total and tamanho_local == tamanho_total:
                log.info(f"  já completo, pulando: {os.path.basename(destino)}")
                return

            headers = dict(HEADERS_BASE)
            modo = "wb"
            if tamanho_local and tamanho_total and tamanho_local < tamanho_total:
                headers["Range"] = f"bytes={tamanho_local}-"
                modo = "ab"
                log.info(f"  retomando download de {os.path.basename(destino)} a partir de {tamanho_local / 1e6:.1f}MB")
            else:
                log.info(f"  baixando {os.path.basename(destino)} " + (f"({tamanho_total / 1e6:.1f}MB)" if tamanho_total else ""))

            with requests.get(url, headers=headers, auth=RFB_AUTH, stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(destino, modo) as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        f.write(chunk)
            return
        except requests.RequestException as e:
            log.warning(f"  falha no download (tentativa {tentativa}/{tentativas}) de {url}: {e}")
            if tentativa == tentativas:
                raise