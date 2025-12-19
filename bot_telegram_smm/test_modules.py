#!/usr/bin/env python3
"""
Script de Teste - Bot Telegram SMM
Valida o funcionamento dos módulos principais do projeto.
"""

import sys
import os

# Adicionar diretório ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Testa se todos os módulos podem ser importados."""
    print("=" * 50)
    print("TESTE DE IMPORTAÇÃO DE MÓDULOS")
    print("=" * 50)
    
    modules = [
        ('config', 'Configurações'),
        ('utils', 'Utilitários'),
        ('pricing', 'Precificação'),
        ('database', 'Banco de Dados'),
        ('api_client', 'Cliente API'),
        ('ocr_processor', 'Processador OCR'),
    ]
    
    all_passed = True
    
    for module_name, description in modules:
        try:
            module = __import__(module_name)
            print(f"✅ {description} ({module_name})")
        except Exception as e:
            print(f"❌ {description} ({module_name}): {e}")
            all_passed = False
    
    return all_passed


def test_pricing():
    """Testa o sistema de precificação."""
    print("\n" + "=" * 50)
    print("TESTE DE PRECIFICAÇÃO")
    print("=" * 50)
    
    import pricing
    
    test_cases = [
        (10.00, 14.00, "Margem fixa (< R$ 20)"),
        (15.00, 19.00, "Margem fixa (< R$ 20)"),
        (20.00, 25.00, "Margem 25% (R$ 20-100)"),
        (50.00, 62.50, "Margem 25% (R$ 20-100)"),
        (100.00, 120.00, "Margem 20% (>= R$ 100)"),
        (200.00, 240.00, "Margem 20% (>= R$ 100)"),
    ]
    
    all_passed = True
    
    for preco_api, esperado, descricao in test_cases:
        resultado, margem, tipo = pricing.calcular_preco_final(preco_api)
        status = "✅" if abs(resultado - esperado) < 0.01 else "❌"
        if status == "❌":
            all_passed = False
        print(f"{status} {descricao}: R$ {preco_api:.2f} → R$ {resultado:.2f} (esperado: R$ {esperado:.2f})")
    
    return all_passed


def test_utils():
    """Testa funções utilitárias."""
    print("\n" + "=" * 50)
    print("TESTE DE UTILITÁRIOS")
    print("=" * 50)
    
    import utils
    
    all_passed = True
    
    # Teste de geração de ID
    pedido_id = utils.gerar_id_pedido()
    status = "✅" if pedido_id.startswith("PED") else "❌"
    if status == "❌":
        all_passed = False
    print(f"{status} Geração de ID: {pedido_id}")
    
    # Teste de validação de URL
    valido, _ = utils.validar_url("https://instagram.com/usuario", "instagram")
    status = "✅" if valido else "❌"
    if status == "❌":
        all_passed = False
    print(f"{status} Validação URL Instagram válida")
    
    valido, _ = utils.validar_url("https://google.com", "instagram")
    status = "✅" if not valido else "❌"
    if status == "❌":
        all_passed = False
    print(f"{status} Validação URL Instagram inválida")
    
    # Teste de validação de quantidade
    valido, qtd, _ = utils.validar_quantidade("1000", 100, 10000)
    status = "✅" if valido and qtd == 1000 else "❌"
    if status == "❌":
        all_passed = False
    print(f"{status} Validação quantidade válida: {qtd}")
    
    valido, _, _ = utils.validar_quantidade("50", 100, 10000)
    status = "✅" if not valido else "❌"
    if status == "❌":
        all_passed = False
    print(f"{status} Validação quantidade abaixo do mínimo")
    
    # Teste de formatação
    valor_formatado = utils.formatar_valor(1234.56)
    status = "✅" if "1.234,56" in valor_formatado else "❌"
    if status == "❌":
        all_passed = False
    print(f"{status} Formatação de valor: {valor_formatado}")
    
    return all_passed


def test_database():
    """Testa operações do banco de dados."""
    print("\n" + "=" * 50)
    print("TESTE DE BANCO DE DADOS")
    print("=" * 50)
    
    import database
    import os
    
    # Usar banco de teste temporário
    test_db = "data/test_pedidos.db"
    
    # Backup do path original
    import config
    original_path = config.DATABASE_PATH
    config.DATABASE_PATH = test_db
    
    all_passed = True
    
    try:
        # Criar diretório se não existir
        os.makedirs("data", exist_ok=True)
        
        # Inicializar banco
        database.inicializar_banco()
        print("✅ Banco de dados inicializado")
        
        # Criar usuário
        novo = database.criar_ou_atualizar_usuario(12345, "teste_user", "Usuário Teste")
        status = "✅" if novo else "❌"
        if status == "❌":
            all_passed = False
        print(f"{status} Usuário criado")
        
        # Obter usuário
        usuario = database.obter_usuario(12345)
        status = "✅" if usuario and usuario['username'] == "teste_user" else "❌"
        if status == "❌":
            all_passed = False
        print(f"{status} Usuário obtido")
        
        # Criar pedido
        pedido_id = database.criar_pedido(
            pedido_id="PED123456789",
            chat_id=12345,
            username="teste_user",
            service_id=1,
            servico_nome="Seguidores Instagram",
            categoria="instagram",
            link="https://instagram.com/teste",
            quantidade=1000,
            preco_api=10.00,
            valor_final=14.00,
            margem_lucro=4.00
        )
        status = "✅" if pedido_id == "PED123456789" else "❌"
        if status == "❌":
            all_passed = False
        print(f"{status} Pedido criado: {pedido_id}")
        
        # Obter pedido
        pedido = database.obter_pedido("PED123456789")
        status = "✅" if pedido and pedido['quantidade'] == 1000 else "❌"
        if status == "❌":
            all_passed = False
        print(f"{status} Pedido obtido")
        
        # Atualizar status
        database.atualizar_status_pedido("PED123456789", "pago")
        pedido = database.obter_pedido("PED123456789")
        status = "✅" if pedido['status'] == "pago" else "❌"
        if status == "❌":
            all_passed = False
        print(f"{status} Status atualizado")
        
        # Estatísticas
        stats = database.obter_estatisticas_gerais()
        status = "✅" if stats['total_pedidos'] >= 1 else "❌"
        if status == "❌":
            all_passed = False
        print(f"{status} Estatísticas obtidas")
        
    except Exception as e:
        print(f"❌ Erro no teste de banco: {e}")
        all_passed = False
    finally:
        # Restaurar path original
        config.DATABASE_PATH = original_path
        # Limpar banco de teste
        if os.path.exists(test_db):
            os.remove(test_db)
    
    return all_passed


def test_ocr():
    """Testa se o Tesseract está funcionando."""
    print("\n" + "=" * 50)
    print("TESTE DE OCR (TESSERACT)")
    print("=" * 50)
    
    import pytesseract
    
    all_passed = True
    
    try:
        # Verificar versão do Tesseract
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract instalado: versão {version}")
        
        # Verificar idiomas disponíveis
        langs = pytesseract.get_languages()
        if 'por' in langs:
            print("✅ Idioma português disponível")
        else:
            print("⚠️ Idioma português não encontrado (pode afetar precisão)")
            all_passed = False
            
    except Exception as e:
        print(f"❌ Tesseract não disponível: {e}")
        all_passed = False
    
    return all_passed


def test_api_client():
    """Testa a estrutura do cliente API."""
    print("\n" + "=" * 50)
    print("TESTE DE CLIENTE API")
    print("=" * 50)
    
    from api_client import BaratoInstaAPI, APIError
    
    all_passed = True
    
    # Verificar se a classe existe e tem os métodos necessários
    api = BaratoInstaAPI()
    
    methods = ['listar_servicos', 'criar_pedido', 'consultar_status', 'consultar_saldo']
    
    for method in methods:
        if hasattr(api, method):
            print(f"✅ Método {method} disponível")
        else:
            print(f"❌ Método {method} não encontrado")
            all_passed = False
    
    # Verificar exceção personalizada
    try:
        raise APIError("Teste de erro")
    except APIError as e:
        print(f"✅ Exceção APIError funcional: {e.message}")
    except Exception:
        print("❌ Exceção APIError não funciona corretamente")
        all_passed = False
    
    return all_passed


def main():
    """Executa todos os testes."""
    print("\n" + "=" * 50)
    print("🧪 INICIANDO TESTES DO BOT TELEGRAM SMM")
    print("=" * 50)
    
    results = []
    
    # Executar testes
    results.append(("Importação de Módulos", test_imports()))
    results.append(("Precificação", test_pricing()))
    results.append(("Utilitários", test_utils()))
    results.append(("Banco de Dados", test_database()))
    results.append(("OCR (Tesseract)", test_ocr()))
    results.append(("Cliente API", test_api_client()))
    
    # Resumo
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS TESTES")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "-" * 50)
    print(f"Total: {passed + failed} | Passou: {passed} | Falhou: {failed}")
    print("=" * 50)
    
    if failed == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print(f"\n⚠️ {failed} teste(s) falharam. Verifique os erros acima.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
