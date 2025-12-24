"""
Processador OCR para Validação de Comprovantes PIX
Utiliza Tesseract OCR e OpenCV para extrair e validar informações de comprovantes.
"""

import re
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Tuple, Dict, List, Optional
from io import BytesIO

import cv2
import numpy as np
from PIL import Image
import pytesseract

import config
import database

# Configurar logging
logger = logging.getLogger(__name__)

# Configurar caminho do Tesseract se especificado
if config.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD


class OCRProcessor:
    """
    Processador de OCR para validação de comprovantes PIX.
    
    Realiza:
    1. Pré-processamento de imagem (melhoria de qualidade)
    2. Extração de texto via Tesseract
    3. Validação de campos do comprovante
    4. Detecção de fraudes (duplicatas)
    
    Example:
        >>> processor = OCRProcessor()
        >>> resultado = processor.processar_comprovante(imagem_bytes, pedido)
        >>> if resultado['valido']:
        ...     print("Comprovante aprovado!")
    """
    
    # Palavras-chave que indicam um comprovante PIX válido
    KEYWORDS_PIX = [
        'pix', 'transferência', 'transferencia', 'pagamento',
        'comprovante', 'recibo', 'transação', 'transacao'
    ]
    
    # Palavras-chave que indicam transação concluída
    KEYWORDS_CONFIRMACAO = [
        'concluído', 'concluido', 'realizada', 'realizado',
        'aprovado', 'aprovada', 'sucesso', 'efetuado', 'efetuada',
        'confirmado', 'confirmada', 'pago', 'paga'
    ]
    
    # Padrões de data comuns em comprovantes
    PADROES_DATA = [
        r'\d{2}/\d{2}/\d{4}',  # DD/MM/YYYY
        r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
        r'\d{2}\.\d{2}\.\d{4}',  # DD.MM.YYYY
        r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
    ]
    
    # Padrões de valor monetário
    PADROES_VALOR = [
        r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2}))',  # R$ 1.234,56
        r'R\$\s*(\d+(?:,\d{2}))',  # R$ 123,45
        r'(\d{1,3}(?:\.\d{3})*(?:,\d{2}))\s*(?:reais|BRL)',  # 123,45 reais
        r'valor[:\s]+R?\$?\s*(\d+[,\.]\d{2})',  # valor: 123,45
    ]
    
    def __init__(self):
        """Inicializa o processador OCR."""
        self.tesseract_config = config.TESSERACT_CONFIG
        
    def melhorar_imagem(self, imagem_bytes: bytes) -> np.ndarray:
        """
        Aplica técnicas de pré-processamento para melhorar a qualidade da imagem.
        
        Etapas:
        1. Conversão para escala de cinza
        2. Aplicação de threshold adaptativo
        3. Redução de ruído
        4. Aumento de contraste (CLAHE)
        
        Args:
            imagem_bytes: Bytes da imagem original
            
        Returns:
            np.ndarray: Imagem processada
        """
        # Converter bytes para array numpy
        nparr = np.frombuffer(imagem_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Não foi possível decodificar a imagem")
        
        # 1. Redimensionar se muito grande (melhora performance)
        altura, largura = img.shape[:2]
        max_dim = 2000
        if max(altura, largura) > max_dim:
            escala = max_dim / max(altura, largura)
            img = cv2.resize(img, None, fx=escala, fy=escala)
        
        # 2. Converter para escala de cinza
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 3. Aplicar threshold adaptativo
        thresh = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        
        # 4. Reduzir ruído
        denoised = cv2.fastNlMeansDenoising(thresh, h=10)
        
        # 5. Aumentar contraste usando CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        logger.debug("Imagem pré-processada com sucesso")
        return enhanced
    
    def extrair_texto(self, imagem: np.ndarray) -> str:
        """
        Extrai texto da imagem usando Tesseract OCR.
        
        Args:
            imagem: Imagem pré-processada (numpy array)
            
        Returns:
            str: Texto extraído
        """
        try:
            texto = pytesseract.image_to_string(
                imagem,
                config=self.tesseract_config
            )
            
            # Limpar texto
            texto = texto.strip()
            texto = re.sub(r'\s+', ' ', texto)  # Normalizar espaços
            
            logger.debug(f"Texto extraído ({len(texto)} caracteres)")
            return texto
            
        except Exception as e:
            logger.error(f"Erro na extração de texto: {e}")
            raise
    
    def extrair_texto_multiplas_configs(self, imagem_bytes: bytes) -> str:
        """
        Tenta extrair texto usando múltiplas configurações do Tesseract.
        Combina os resultados para melhor cobertura.
        
        Args:
            imagem_bytes: Bytes da imagem original
            
        Returns:
            str: Texto combinado de todas as tentativas
        """
        configs = [
            '--psm 6 --oem 3 -l por',  # Bloco de texto uniforme
            '--psm 4 --oem 3 -l por',  # Coluna única de texto variável
            '--psm 3 --oem 3 -l por',  # Segmentação automática
        ]
        
        textos = []
        
        # Processar imagem original
        imagem_melhorada = self.melhorar_imagem(imagem_bytes)
        
        for cfg in configs:
            try:
                texto = pytesseract.image_to_string(imagem_melhorada, config=cfg)
                textos.append(texto)
            except Exception as e:
                logger.warning(f"Erro com config {cfg}: {e}")
        
        # Também tentar com imagem original (sem pré-processamento)
        try:
            nparr = np.frombuffer(imagem_bytes, np.uint8)
            img_original = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            texto_original = pytesseract.image_to_string(
                img_original,
                config='--psm 6 --oem 3 -l por'
            )
            textos.append(texto_original)
        except Exception:
            pass
        
        # Combinar textos únicos
        texto_combinado = ' '.join(set(' '.join(textos).split()))
        return texto_combinado.lower()
    
    def verificar_valor(self, texto: str, valor_esperado: float) -> Tuple[bool, Optional[float]]:
        """
        Verifica se o valor no comprovante corresponde ao esperado.
        
        Args:
            texto: Texto extraído do comprovante
            valor_esperado: Valor que deveria estar no comprovante
            
        Returns:
            Tuple[bool, Optional[float]]: (valor_encontrado, valor_extraido)
        """
        valores_encontrados = []
        
        for padrao in self.PADROES_VALOR:
            matches = re.findall(padrao, texto, re.IGNORECASE)
            for match in matches:
                try:
                    # Normalizar formato do valor
                    valor_str = match.replace('.', '').replace(',', '.')
                    valor = float(valor_str)
                    valores_encontrados.append(valor)
                except ValueError:
                    continue
        
        logger.debug(f"Valores encontrados: {valores_encontrados}")
        
        # Verificar se algum valor corresponde (com tolerância)
        tolerancia = config.TOLERANCIA_VALOR
        for valor in valores_encontrados:
            if abs(valor - valor_esperado) <= tolerancia:
                logger.info(f"Valor correspondente encontrado: {valor}")
                return True, valor
        
        # Retornar o valor mais próximo encontrado (para log)
        if valores_encontrados:
            valor_mais_proximo = min(valores_encontrados, key=lambda x: abs(x - valor_esperado))
            return False, valor_mais_proximo
        
        return False, None
    
    def verificar_data(self, texto: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica se a data no comprovante é recente (hoje ou ontem).
        
        Args:
            texto: Texto extraído do comprovante
            
        Returns:
            Tuple[bool, Optional[str]]: (data_valida, data_encontrada)
        """
        hoje = datetime.now().date()
        ontem = hoje - timedelta(days=1)
        
        datas_validas = [
            hoje.strftime('%d/%m/%Y'),
            hoje.strftime('%d-%m-%Y'),
            hoje.strftime('%d.%m.%Y'),
            ontem.strftime('%d/%m/%Y'),
            ontem.strftime('%d-%m-%Y'),
            ontem.strftime('%d.%m.%Y'),
        ]
        
        for padrao in self.PADROES_DATA:
            matches = re.findall(padrao, texto)
            for match in matches:
                # Normalizar formato
                data_normalizada = match.replace('-', '/').replace('.', '/')
                
                if data_normalizada in [d.replace('-', '/').replace('.', '/') for d in datas_validas]:
                    logger.info(f"Data válida encontrada: {match}")
                    return True, match
                    
                # Verificar formato YYYY-MM-DD
                try:
                    data_obj = datetime.strptime(match, '%Y-%m-%d').date()
                    if data_obj in [hoje, ontem]:
                        return True, match
                except ValueError:
                    pass
        
        # Retornar primeira data encontrada (para log)
        for padrao in self.PADROES_DATA:
            matches = re.findall(padrao, texto)
            if matches:
                return False, matches[0]
        
        return False, None
    
    def verificar_keywords_pix(self, texto: str) -> bool:
        """
        Verifica se o texto contém palavras-chave de PIX.
        
        Args:
            texto: Texto extraído do comprovante
            
        Returns:
            bool: True se contém palavras-chave de PIX
        """
        texto_lower = texto.lower()
        encontradas = [kw for kw in self.KEYWORDS_PIX if kw in texto_lower]
        
        if encontradas:
            logger.debug(f"Keywords PIX encontradas: {encontradas}")
            return True
        return False
    
    def verificar_confirmacao(self, texto: str) -> bool:
        """
        Verifica se o texto indica transação concluída.
        
        Args:
            texto: Texto extraído do comprovante
            
        Returns:
            bool: True se indica transação concluída
        """
        texto_lower = texto.lower()
        encontradas = [kw for kw in self.KEYWORDS_CONFIRMACAO if kw in texto_lower]
        
        if encontradas:
            logger.debug(f"Keywords confirmação encontradas: {encontradas}")
            return True
        return False
    
    def verificar_duplicata(self, imagem_bytes: bytes, chat_id: int) -> Tuple[bool, Optional[Dict]]:
        """
        Verifica se o comprovante já foi usado anteriormente.
        
        Args:
            imagem_bytes: Bytes da imagem
            chat_id: ID do chat do usuário
            
        Returns:
            Tuple[bool, Optional[Dict]]: (é_duplicata, dados_uso_anterior)
        """
        hash_comprovante = hashlib.md5(imagem_bytes).hexdigest()
        
        uso_anterior = database.verificar_comprovante_duplicado(hash_comprovante)
        
        if uso_anterior:
            logger.warning(f"Comprovante duplicado detectado! Hash: {hash_comprovante}")
            return True, uso_anterior
        
        return False, None
    
    def processar_comprovante(
        self, 
        imagem_bytes: bytes, 
        pedido: Dict
    ) -> Dict:
        """
        Processa e valida um comprovante de pagamento.
        
        Args:
            imagem_bytes: Bytes da imagem do comprovante
            pedido: Dict com dados do pedido (deve conter 'valor_final', 'id', 'chat_id')
            
        Returns:
            Dict com resultado da validação:
            {
                'valido': bool,
                'aprovacao_automatica': bool,
                'motivo': str,
                'detalhes': {
                    'tem_pix': bool,
                    'valor_correto': bool,
                    'valor_encontrado': float,
                    'data_valida': bool,
                    'data_encontrada': str,
                    'tem_confirmacao': bool,
                    'texto_extraido': str,
                    'hash': str
                }
            }
        """
        resultado = {
            'valido': False,
            'aprovacao_automatica': False,
            'motivo': '',
            'detalhes': {
                'tem_pix': False,
                'valor_correto': False,
                'valor_encontrado': None,
                'data_valida': False,
                'data_encontrada': None,
                'tem_confirmacao': False,
                'texto_extraido': '',
                'hash': ''
            }
        }
        
        try:
            # 1. Verificar duplicata
            hash_comprovante = hashlib.md5(imagem_bytes).hexdigest()
            resultado['detalhes']['hash'] = hash_comprovante
            
            eh_duplicata, uso_anterior = self.verificar_duplicata(imagem_bytes, pedido['chat_id'])
            if eh_duplicata:
                resultado['motivo'] = 'Comprovante já utilizado anteriormente'
                resultado['detalhes']['duplicata'] = True
                resultado['detalhes']['uso_anterior'] = uso_anterior
                
                # Log de tentativa de fraude
                logger.warning(f"Fraude detectada: comprovante duplicado para pedido {pedido['id']}")

                
                return resultado
            
            # 2. Extrair texto
            texto = self.extrair_texto_multiplas_configs(imagem_bytes)
            resultado['detalhes']['texto_extraido'] = texto[:500]  # Limitar tamanho
            
            if not texto or len(texto) < 20:
                resultado['motivo'] = 'Não foi possível ler o comprovante. Envie uma imagem mais nítida.'
                return resultado
            
            # 3. Verificar keywords PIX
            tem_pix = self.verificar_keywords_pix(texto)
            resultado['detalhes']['tem_pix'] = tem_pix
            
            # 4. Verificar valor
            valor_correto, valor_encontrado = self.verificar_valor(texto, pedido['valor_final'])
            resultado['detalhes']['valor_correto'] = valor_correto
            resultado['detalhes']['valor_encontrado'] = valor_encontrado
            
            # 5. Verificar data
            data_valida, data_encontrada = self.verificar_data(texto)
            resultado['detalhes']['data_valida'] = data_valida
            resultado['detalhes']['data_encontrada'] = data_encontrada
            
            # 6. Verificar confirmação
            tem_confirmacao = self.verificar_confirmacao(texto)
            resultado['detalhes']['tem_confirmacao'] = tem_confirmacao
            
            # 7. Determinar resultado
            validacoes = {
                'tem_pix': tem_pix,
                'valor_correto': valor_correto,
                'data_valida': data_valida,
                'tem_confirmacao': tem_confirmacao
            }
            
            # Aprovação automática: todas as validações passam
            if all(validacoes.values()):
                resultado['valido'] = True
                resultado['aprovacao_automatica'] = True
                resultado['motivo'] = 'Comprovante válido'
                
                # Registrar hash do comprovante
                database.registrar_uso_comprovante(hash_comprovante, pedido['id'], pedido['chat_id'])
                
                logger.info(f"Comprovante aprovado automaticamente para pedido {pedido['id']}")
                
            # Aprovação manual: algumas validações falham mas não é fraude clara
            elif tem_pix and (valor_correto or tem_confirmacao):
                resultado['valido'] = True
                resultado['aprovacao_automatica'] = False
                
                # Determinar motivo para análise manual
                motivos = []
                if not valor_correto:
                    if valor_encontrado:
                        motivos.append(f"Valor diferente (encontrado: R$ {valor_encontrado:.2f})")
                    else:
                        motivos.append("Valor não identificado")
                if not data_valida:
                    if data_encontrada:
                        motivos.append(f"Data não é de hoje/ontem ({data_encontrada})")
                    else:
                        motivos.append("Data não identificada")
                if not tem_confirmacao:
                    motivos.append("Status de confirmação não identificado")
                
                resultado['motivo'] = ' | '.join(motivos)
                
                logger.info(f"Comprovante enviado para aprovação manual: {resultado['motivo']}")
                
            # Rejeição: não parece ser um comprovante válido
            else:
                resultado['valido'] = False
                resultado['aprovacao_automatica'] = False
                
                if not tem_pix:
                    resultado['motivo'] = 'Não parece ser um comprovante PIX'
                elif not valor_correto and valor_encontrado:
                    resultado['motivo'] = f'Valor incorreto. Esperado: R$ {pedido["valor_final"]:.2f}, Encontrado: R$ {valor_encontrado:.2f}'
                elif not valor_correto:
                    resultado['motivo'] = 'Valor do pagamento não identificado'
                else:
                    resultado['motivo'] = 'Comprovante não pôde ser validado'
                
                logger.warning(f"Comprovante rejeitado para pedido {pedido['id']}: {resultado['motivo']}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao processar comprovante: {e}")
            resultado['motivo'] = 'Erro ao processar imagem. Tente novamente.'
            return resultado


# Instância global do processador
ocr_processor = OCRProcessor()


# ==========================================
# FUNÇÕES DE CONVENIÊNCIA
# ==========================================

def processar_comprovante(imagem_bytes: bytes, pedido: Dict) -> Dict:
    """Wrapper para ocr_processor.processar_comprovante()"""
    return ocr_processor.processar_comprovante(imagem_bytes, pedido)


def calcular_hash_comprovante(imagem_bytes: bytes) -> str:
    """Calcula o hash MD5 de um comprovante."""
    return hashlib.md5(imagem_bytes).hexdigest()
