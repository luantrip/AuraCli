---
name: SOLID Principles of Object-Oriented Design
description: Use this skill to understand, apply, and explain the five SOLID principles of object-oriented design (Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion). This is a foundational skill for writing clean, maintainable, and scalable software.
version: 1.0.0
author: Aura Core Team
---

# Guia de Referência: Princípios SOLID

Os princípios SOLID são cinco diretrizes de design para o desenvolvimento de software orientado a objetos que o tornam mais fácil de entender, manter e estender. Eles foram promovidos por Robert C. Martin.

## 1. (S) Princípio da Responsabilidade Única (Single Responsibility Principle - SRP)

**"Uma classe deve ter um, e apenas um, motivo para mudar."**

### Conceito
Cada classe ou módulo deve ter responsabilidade sobre uma única parte da funcionalidade da aplicação. Se uma classe tem mais de uma responsabilidade, ela se torna acoplada. Uma mudança em uma responsabilidade pode afetar e introduzir bugs em outra.

### Exemplo

**NÃO FAÇA (Múltiplas Responsabilidades):**
```python
class Relatorio:
    def gerar_dados(self, dados):
        # Lógica para processar e formatar dados
        print("Gerando dados para o relatório...")
        return "dados formatados"

    def salvar_em_arquivo(self, dados_formatados, caminho):
        # Lógica para escrever em um arquivo
        print(f"Salvando relatório em {caminho}...")
        with open(caminho, "w") as f:
            f.write(dados_formatados)
```
*Violação:* A classe `Relatorio` tem duas responsabilidades: gerar os dados e persistir os dados. Uma mudança no formato de persistência (ex: salvar em JSON em vez de TXT) forçaria uma mudança na classe `Relatorio`.

**FAÇA (Responsabilidades Separadas):**
```python
class GeradorDeRelatorio:
    def gerar(self, dados):
        print("Gerando dados para o relatório...")
        return "dados formatados"


class PersistenciaDeRelatorio:
    def salvar(self, dados_formatados, caminho):
        print(f"Salvando relatório em {caminho}...")
        with open(caminho, "w") as f:
            f.write(dados_formatados)
```
*Correção:* Cada classe agora tem uma única responsabilidade. `GeradorDeRelatorio` só se preocupa com a lógica de negócios, e `PersistenciaDeRelatorio` só se preocupa com a persistência.

## 2. (O) Princípio do Aberto/Fechado (Open/Closed Principle - OCP)

**"Entidades de software (classes, módulos, funções) devem ser abertas para extensão, mas fechadas para modificação."**

### Conceito
Você deve ser capaz de adicionar novas funcionalidades a uma classe sem alterar seu código-fonte existente. Isso é geralmente alcançado através de herança, polimorfismo ou padrões de design como o Strategy.

### Exemplo

**NÃO FAÇA (Modificação Necessária):**
```python
class Desconto:
    def aplicar(self, valor, tipo_cliente):
        if tipo_cliente == "normal":
            return valor * 0.95
        elif tipo_cliente == "vip":
            return valor * 0.85
        # Para adicionar um novo tipo 'premium', eu preciso MODIFICAR esta classe.
```
*Violação:* Para adicionar um novo tipo de desconto, a classe `Desconto` precisa ser modificada, o que pode introduzir bugs.

**FAÇA (Aberto para Extensão):**
```python
from abc import ABC, abstractmethod


class EstrategiaDeDesconto(ABC):
    @abstractmethod
    def aplicar_desconto(self, valor):
        pass


class DescontoNormal(EstrategiaDeDesconto):
    def aplicar_desconto(self, valor):
        return valor * 0.95


class DescontoVip(EstrategiaDeDesconto):
    def aplicar_desconto(self, valor):
        return valor * 0.85


# Nova funcionalidade sem modificar o código existente!
class DescontoPremium(EstrategiaDeDesconto):
    def aplicar_desconto(self, valor):
        return valor * 0.75


class CalculadoraDePreco:
    def calcular(self, valor, estrategia: EstrategiaDeDesconto):
        return estrategia.aplicar_desconto(valor)
```
*Correção:* A lógica é estendida criando novas classes que implementam a abstração `EstrategiaDeDesconto`. A `CalculadoraDePreco` não precisa ser modificada para suportar novos tipos de desconto.

## 3. (L) Princípio da Substituição de Liskov (Liskov Substitution Principle - LSP)

**"Subtipos devem ser substituíveis por seus tipos base."**

### Conceito
Se a classe `A` é um subtipo da classe `B`, então instâncias da classe `B` devem poder ser substituídas por instâncias da classe `A` sem alterar o comportamento esperado do programa. Essencialmente, uma subclasse não deve quebrar a funcionalidade da sua superclasse.

### Exemplo

**NÃO FAÇA (Comportamento Inesperado):**
```python
class Passaro:
    def voar(self):
        print("Voando...")


class Pinguim(Passaro):
    def voar(self):
        raise Exception("Pinguins não podem voar!")


def fazer_passaro_voar(passaro: Passaro):
    passaro.voar()


# fazer_passaro_voar(Pinguim()) # Isso quebraria o programa!
```
*Violação:* Um `Pinguim` é um `Passaro`, mas não pode `voar` como o tipo base. Portanto, não é substituível.

**FAÇA (Hierarquia Coerente):**
```python
class Passaro:
    pass  # Classe base mais genérica


class PassaroVoador(Passaro):
    def voar(self):
        print("Voando...")


class PassaroNaoVoador(Passaro):
    pass  # Não tem o método voar


class Pinguim(PassaroNaoVoador):
    def nadar(self):
        print("Nadando...")


def fazer_passaro_voar(passaro: PassaroVoador):
    passaro.voar()
```
*Correção:* A hierarquia de classes agora representa corretamente as capacidades. O código que espera um `PassaroVoador` nunca receberá um `Pinguim`.

## 4. (I) Princípio da Segregação de Interfaces (Interface Segregation Principle - ISP)

**"Nenhum cliente deve ser forçado a depender de métodos que não utiliza."**

### Conceito
É melhor ter muitas interfaces específicas para o cliente do que uma única interface de propósito geral. Classes não devem ser forçadas a implementar métodos que não usarão.

### Exemplo

**NÃO FAÇA (Interface "Gorda"):**
```python
from abc import ABC, abstractmethod


class Maquina(ABC):
    @abstractmethod
    def imprimir(self, documento):
        pass

    @abstractmethod
    def escanear(self, documento):
        pass

    @abstractmethod
    def enviar_fax(self, documento):
        pass


class ImpressoraSimples(Maquina):
    def imprimir(self, documento):
        print("Imprimindo...")

    def escanear(self, documento):
        # Não faz nada, viola o ISP
        pass

    def enviar_fax(self, documento):
        # Não faz nada, viola o ISP
        pass
```
*Violação:* `ImpressoraSimples` é forçada a implementar métodos `escanear` e `enviar_fax` que não utiliza.

**FAÇA (Interfaces Segregadas):**
```python
class Impressora(ABC):
    @abstractmethod
    def imprimir(self, documento):
        pass


class Scanner(ABC):
    @abstractmethod
    def escanear(self, documento):
        pass


class ImpressoraSimples(Impressora):
    def imprimir(self, documento):
        print("Imprimindo...")


class MaquinaMultiFuncional(Impressora, Scanner):
    def imprimir(self, documento):
        print("Imprimindo...")

    def escanear(self, documento):
        print("Escaneando...")
```
*Correção:* As interfaces são pequenas e focadas. As classes implementam apenas as interfaces que fazem sentido para elas.

## 5. (D) Princípio da Inversão de Dependência (Dependency Inversion Principle - DIP)

**"A. Módulos de alto nível não devem depender de módulos de baixo nível. Ambos devem depender de abstrações."**
**"B. Abstrações não devem depender de detalhes. Detalhes devem depender de abstrações."**

### Conceito
Este princípio visa desacoplar os módulos de software. Em vez de o código de alto nível (lógica de negócios) depender diretamente do código de baixo nível (detalhes de implementação, como banco de dados, APIs), ambos devem depender de uma interface (abstração). A Injeção de Dependência é uma maneira comum de implementar este princípio.

### Exemplo

**NÃO FAÇA (Dependência Direta):**
```python
class Notificador:
    def __init__(self):
        # Dependência direta de uma classe concreta
        self.servico_email = ServicoDeEmailGmail()

    def enviar_notificacao(self, mensagem):
        self.servico_email.enviar(mensagem)


class ServicoDeEmailGmail:
    def enviar(self, mensagem):
        print(f"Enviando email via Gmail: {mensagem}")
```
*Violação:* O `Notificador` (alto nível) está diretamente acoplado ao `ServicoDeEmailGmail` (baixo nível). Para usar um serviço diferente (ex: SendGrid), seria necessário modificar a classe `Notificador`.

**FAÇA (Depender de Abstrações):**
```python
class InterfaceServicoDeEmail(ABC):
    @abstractmethod
    def enviar(self, mensagem):
        pass


class ServicoDeEmailGmail(InterfaceServicoDeEmail):
    def enviar(self, mensagem):
        print(f"Enviando email via Gmail: {mensagem}")


class ServicoDeEmailSendGrid(InterfaceServicoDeEmail):
    def enviar(self, mensagem):
        print(f"Enviando email via SendGrid: {mensagem}")


class Notificador:
    # A dependência é "injetada" no construtor
    def __init__(self, servico_email: InterfaceServicoDeEmail):
        self.servico_email = servico_email

    def enviar_notificacao(self, mensagem):
        self.servico_email.enviar(mensagem)


# Uso
gmail = ServicoDeEmailGmail()
notificador_gmail = Notificador(gmail)

sendgrid = ServicoDeEmailSendGrid()
notificador_sendgrid = Notificador(sendgrid)
```
*Correção:* O `Notificador` agora depende da abstração `InterfaceServicoDeEmail`, não de uma implementação concreta. Podemos "injetar" qualquer serviço que siga essa interface sem alterar o `Notificador`.
