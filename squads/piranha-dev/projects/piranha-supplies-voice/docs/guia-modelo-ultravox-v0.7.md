# Guia — Migração para ultravox-v0.7

**Projecto:** piranha-supplies-voice
**Data:** Março 2026
**Squad:** piranha-dev

---

## Contexto

O modelo anterior (`ultravox-v0.6-llama3.3-70b` / Llama 3.3 70B) apresentou nos testes um problema de cadência: o agente falava demasiado rápido, sem pausas perceptíveis entre perguntas e afirmações, tornando difícil perceber onde terminava uma ideia e começava outra.

A migração para `ultravox-v0.7` resolve este problema de duas formas:
1. O modelo base é diferente (Ultravox v0.7 — arquitetura própria da Fixie AI, não baseada em Llama)
2. O system prompt foi ajustado com uma secção explícita de ritmo e cadência

---

## O que mudou no código

### `src/clients/ultravox.py`

| Campo | Antes | Depois |
|-------|-------|--------|
| `MODEL` | `ultravox-v0.6-llama3.3-70b` | `ultravox-v0.7` |
| `temperature` | `0.7` | `0.4` |

**Porquê temperature 0.4?**
Com temperatura mais baixa, o modelo é mais previsível e consistente no ritmo. Valores altos (0.7–1.0) produzem variações maiores na geração, o que resulta em ritmo irregular e respostas mais longas do que o necessário numa chamada de voz.

### `src/prompts/feedback_agent.py`

Adicionada a secção **"Ritmo e cadência de fala"** logo após a descrição de tom. Esta secção contém regras explícitas sobre:
- Falar devagar e articulado
- Diferença de ritmo entre perguntas e afirmações
- Máximo de uma pergunta por turno
- Silêncio após perguntar
- Máximo de duas frases por resposta

---

## Modelos disponíveis na conta Ultravox (Março 2026)

| Model ID | Base | Custo aprox. | Notas |
|----------|------|--------------|-------|
| `ultravox-v0.7` | Proprietário Fixie AI | — | **Recomendado agora** |
| `ultravox-v0.6-llama3.3-70b` | Meta Llama 3.3 70B | $0.05/min | Testado — voz rápida |
| `ultravox-v0.6-gemma3-27b` | Google Gemma 3 27B | — | Não testado |
| `ultravox-v0.6` | Proprietário | — | Versão anterior |

---

## Como trocar de modelo

Edita apenas uma linha em `src/clients/ultravox.py`:

```python
# ultravox-v0.7 (recomendado)
MODEL = "ultravox-v0.7"

# llama 3.3 70B (se quiser comparar)
MODEL = "ultravox-v0.6-llama3.3-70b"

# gemma (para testar)
MODEL = "ultravox-v0.6-gemma3-27b"
```

Depois, deploy:
```bash
bash deploy/push-to-vps.sh
ssh root@144.91.85.135
cd /opt/piranha-supplies-voice && bash deploy/setup.sh
docker service update --force piranha-voice_piranha_voice
```

---

## Como testar após deploy

```bash
curl -X POST https://call.piranhasupplies.com/admin/test-call \
  -H "Content-Type: application/json" \
  -d '{
    "to_number": "+351XXXXXXXXX",
    "name": "Pedro",
    "country_code": "PT",
    "products": [{"title": "Máquina Rotativa Hawk Pen", "price": "189.90"}],
    "total_price": "189.90"
  }'
```

---

## Critérios de avaliação do teste de voz

Ao testar, avaliar estes pontos:

| Critério | Resultado esperado |
|----------|--------------------|
| Ritmo | Calmo, pausado — não robotizado, mas claramente articulado |
| Perguntas | Tom ligeiramente ascendente no final, seguido de silêncio |
| Afirmações | Tom descendente e pausa antes da próxima frase |
| Uma pergunta de cada vez | O agente não acumula perguntas numa mesma resposta |
| Abertura | Espera que o cliente fale primeiro (firstSpeakerSettings: user) |
| Identificação | Diz sempre "clone de IA do Pedro, da Piranha Supplies" |
| Aviso de gravação | Menciona no início que a chamada pode ser gravada |

---

## Configuração completa da chamada (referência)

```python
# src/clients/ultravox.py
MODEL = "ultravox-v0.7"
temperature = 0.4
firstSpeakerSettings = {"user": {}}   # outbound — cliente fala primeiro
medium = {"twilio": {}}               # Twilio Media Streams

# Voz
externalVoice = {
    "cartesia": {
        "voiceId": "b709d0a2-7fcd-4c24-9789-e8b065430a63",
        "model": "sonic-3"
    }
}

# Tools built-in
selectedTools = [
    {"toolId": "56294126-5a7d-4948-b67d-3b7e13d55ae7"},                         # hangUp
    {"toolId": "2fff509d-273f-414e-91ff-aa933435a545",
     "parameterOverrides": {"target": "+351232468548"}},                         # coldTransfer → suporte humano
    {"toolId": "84a31bac-5c1b-41c3-9058-f81acb7ffaa7",
     "parameterOverrides": {"corpus_id": "06436a6f-e604-4959-b15b-ca0b181c4a4c"}}, # queryCorpus → RAG Piranha Info
    {"toolId": "8721c74d-af3f-4dfa-a736-3bc170ef917c"},                         # leaveVoicemail
]
```

---

## Notas para o squad

**Se a voz ainda falar rápido com v0.7:**
O problema pode estar na voz Cartesia, não no modelo LLM. A Cartesia Sonic 3 tem parâmetros de velocidade que podem ser configurados. Neste momento a velocidade é a padrão (1.0). Para testar com velocidade mais lenta, seria necessário passar `speed` na configuração Cartesia — mas isto ainda não está exposto via Ultravox BYOK. Confirmar com a Ultravox se `externalVoice.cartesia` suporta este campo.

**Se quiser comparar dois modelos em testes separados:**
Fazer dois deploys em momentos distintos e documentar a chamada de teste com as mesmas variáveis de entrada para comparação justa.

**A variável `temperature`:**
Se com 0.4 o agente soar demasiado mecânico, aumentar progressivamente: 0.4 → 0.5 → 0.6. Não ultrapassar 0.7 para chamadas de voz.
