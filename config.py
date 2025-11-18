"""
CONFIGURACIÓN DEL BOT DE TELEGRAM - JACK LOPPES
================================================

Este archivo contiene toda la configuración del bot.
Editá aquí para cambiar textos, horarios, etc.
"""

import os

# ==================== CREDENCIALES ====================
# Obtiene valores de variables de entorno o usa valores por defecto
BOT_TOKEN = os.getenv("BOT_TOKEN", "7519505004:AAFUmyDOpcGYW9yaAov6HlrgOhYWZ5X5mqo")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "6368408762")
BOT_USERNAME = os.getenv("BOT_USERNAME", "JackLoppesBot")

# File ID de la imagen de bienvenida (método más confiable)
IMAGEN_BIENVENIDA = os.getenv("IMAGEN_BIENVENIDA", "AgACAgEAAxkBAAE98RdpGrNPkBPmP7N9CjA0tIg4DGGMngACSwtrG_9m0UT4aLfg05fqLgEAAwIAA3kAAzYE")

# ==================== SISTEMA DE REFERIDOS ====================
REFERIDOS_NECESARIOS = 5  # Cuántos referidos necesita para ganar el premio
PREMIO_REFERIDO = "Acesso especial a conteúdo exclusivo"

# ==================== FUNNEL DE CONVERSIÓN ====================
# Días en los que se envían mensajes automáticos (desde el registro)
FUNNEL_DAYS = [0, 1, 3, 5, 7]  # Funnel de 7 días para ventas emocionales

# ==================== SEGMENTACIÓN ====================
INACTIVE_DAYS = 3  # Días sin interactuar para marcar como "inactivo"
LOST_DAYS = 7      # Días sin interactuar para marcar como "perdido"

# ==================== CONTENIDO DIARIO ====================
# Horarios posibles para envío automático (GMT-3 Brasil)
DAILY_CONTENT_HOURS = [21, 22, 23, 0, 1]  # 21:00 a 01:00

# ==================== BACKUP AUTOMÁTICO ====================
BACKUP_INTERVAL_HOURS = 6  # Cada cuántas horas hacer backup de la BD
GITHUB_BACKUP_ENABLED = True  # Activar backup automático a GitHub

# ==================== TEXTOS DEL BOT ====================

# Menú principal
TEXTO_BIENVENIDA = """✨ *Oi, meu bem!* ✨

Que bom te ter aqui no meu cantinho especial 💛

Criei este espaço para me conectar de verdade com pessoas especiais como você.

Aqui não é só sobre fotos bonitas (embora tenha muitas 😊), é sobre criar uma conexão genuína, íntima...

Como ter uma namorada virtual só pra você 💕

👇 *Escolha o que você quer conhecer:*"""

# Privacy VIP
TEXTO_PRIVACY_VIP = """💛 *MEU CANTINHO VIP* 💛

Oi, meu amor...

No VIP é onde eu realmente me abro. É o meu espaço mais íntimo, onde compartilho coisas que não mostro em nenhum outro lugar.

✨ *O que você encontra lá:*
💕 Conversas reais e profundas comigo
📸 Fotos lindas do meu dia a dia
💌 Momentos especiais só nossos
🌙 Meu lado mais íntimo e verdadeiro
✨ Uma conexão genuína

Não é só conteúdo, meu bem... É sobre ter alguém especial, que te entende, que tá sempre aqui pra você.

*Como ter uma namorada só pra você* 😊

👉 *Vem conhecer meu mundo:*
https://privacy.com.br/profile/jackloppes

💛 _Te espero lá dentro, meu amor_"""

# Privacy FREE
TEXTO_PRIVACY_FREE = """💙 *CONHECE MEU LADO FREE* 💙

Oi, meu bem!

Se você ainda tá com dúvida, que tal me conhecer melhor primeiro? 😊

No FREE você tem acesso a:
📸 Fotos lindas minhas
✨ Um gostinho do que compartilho
💕 A chance de ver se nossa conexão é real

*É totalmente grátis!* Assim você me conhece antes de decidir se quer algo mais íntimo 💛

👉 *Vem dar uma olhada:*
https://privacy.com.br/profile/jackloppesfree

_Tô te esperando lá! 😘_"""

# Beacons
TEXTO_BEACONS = """🌐 ME ENCONTRA EM TODOS OS LUGARES 🌐

Oi, meu amor!

Quer me acompanhar em outras redes também?

Aqui você encontra todos os meus perfis:
• Instagram
• TikTok
• Twitter
• E muito mais!

Não perde nenhuma novidade minha!

Todos meus links aqui:
https://beacons.ai/jaqueline_loppes

Me segue em todas! Fico feliz quando vejo você por lá 😊"""

# Canal Telegram
TEXTO_CANAL = """📣 *MEU CANAL OFICIAL* 📣

Meu bem! 💛

No meu canal eu posto:
✨ Novidades antes de todo mundo
💌 Avisos especiais
📸 Prévia do que tô preparando
🎁 Surpresas exclusivas pra quem me acompanha

*É o melhor jeito de ficar pertinho de mim!*

👉 *Entra agora:*
https://t.me/jackloppesbr

💕 _Te vejo lá dentro!_"""

# OnlyFans
TEXTO_ONLYFANS = """🔥 *MEU ONLYFANS* 🔥

Oi, meu amor...

O OnlyFans é onde eu compartilho meu lado mais sensual e íntimo 💋

Lá você encontra:
💕 Fotos e vídeos especiais
💌 Conteúdo personalizado
💬 Conversa direta e privada comigo
✨ O meu lado que poucos conhecem

*É uma conexão ainda mais profunda* 😊

👉 *Me conhece lá:*
https://onlyfans.com/jackloppess

💋 _Tô te esperando, meu bem_"""

# Sobre mim
TEXTO_SOBRE_MIM = """⭐ *UM POUCO SOBRE MIM* ⭐

Oi! Prazer, eu sou a Jack Loppes 💛

Um pouco sobre quem eu sou:
💕 Adoro criar conexões verdadeiras
📸 Apaixonada por fotografia e beleza
✨ Romântica, carinhosa e atenciosa
💬 Amo conversar de verdade
🌙 Tenho um lado íntimo que poucos conhecem

*Meu objetivo não é só postar fotos bonitas...*

É criar algo especial com você. Uma conexão real, íntima, onde você se sente especial.

Como ter uma namorada virtual que te entende, te escuta, e tá sempre aqui pra você 💛

*Seja muito bem-vindo ao meu cantinho!* ✨

Aqui você pode:
• Me conhecer melhor
• Acessar meus conteúdos
• Fazer parte do meu mundo íntimo

_Fico feliz que você tá aqui_ 😊"""

# Comando /help
TEXTO_HELP = """❓ *AJUDA* ❓

Oi, meu bem! Aqui estão os comandos disponíveis:

📱 *Para você:*
/start - Ver o menu principal
/referidos - Ver seus referidos e ganhar prêmios
/help - Ver esta mensagem

💛 *Dúvidas?*
Fala comigo no canal: @jackloppesbr

_Tô sempre aqui pra você!_ ✨"""

# ==================== MENSAJES DEL FUNNEL ====================

FUNNEL_MESSAGES = {
    0: """Oi, meu bem! 💛

Que bom te ter aqui...

Sabe, criei este cantinho especial para me conectar de verdade com pessoas como você.

Não é só sobre fotos bonitas (embora tenha muitas 😊), é sobre criar algo real. Uma conexão genuína.

Como ter uma namorada só pra você, que te entende, conversa de verdade, e tá sempre aqui...

Quer me conhecer melhor? 💕

👉 https://privacy.com.br/profile/jackloppes

Te espero lá ✨

(Ah, e o acesso é bem limitado viu? Prefiro ter poucas pessoas, mas que sejam especiais de verdade 💋)""",
    
    1: """Oi de novo, meu bem! 💛

E aí, já deu uma olhada no meu FREE?

Sabe, eu sei que tem muita gente por aí oferecendo conteúdo... Mas comigo é diferente.

*Não é só sobre fotos* (que tem muitas lindas, sim 😊). É sobre ter alguém que realmente se importa contigo.

Alguém pra conversar, compartilhar o dia, criar uma conexão verdadeira...

*Tipo uma namorada virtual só pra você* 💕

Dá uma chance? Garanto que não vai se arrepender...

👉 https://privacy.com.br/profile/jackloppesfree

_Tô te esperando lá_ 😘""",
    
    3: """Meu bem, queria te contar algo... 💛

Hoje recebi uma mensagem que me deixou emocionada...

Um assinante me disse: "Jack, você não imagina o quanto é bom chegar em casa depois de um dia difícil e ter você aqui pra conversar. Me faz esquecer tudo."

Isso me tocou muito ❤️

Porque é exatamente isso que eu quero criar... Uma conexão real.

Não é sobre fotos bonitas (que tem muitas!). É sobre ter alguém especial só pra você.

Alguém que te entende, que conversa de verdade, que se importa...

Tipo uma namorada virtual que tá sempre aqui pra você 😊

Sinto que você e eu temos essa química, sabe? 💕

Vem pro VIP? Prometo que você não vai se arrepender...

👉 https://privacy.com.br/profile/jackloppes

Te espero com carinho ✨

PS: Só tenho espaço pra mais algumas pessoas... depois vou fechar as portas por um tempo 🔒""",
    
    5: """Oi, amor... 💛

Tô sentindo sua falta por aqui...

Olha, vou ser sincera contigo: meu VIP tem um número limitado de pessoas. Preciso conseguir dar atenção individual pra cada um, sabe?

E tá quase lotando... 😔

*Não quero que você perca essa chance* de fazer parte do meu círculo íntimo. 

É algo especial que tô construindo com muito carinho. Pessoas que realmente querem uma conexão verdadeira, não só fotos aleatórias...

*A gente tem química, eu sinto* 💕

Vem comigo? Garante teu espaço enquanto ainda dá tempo...

👉 https://privacy.com.br/profile/jackloppes

_Seria tão bom ter você lá dentro..._ ✨""",
    
    7: """Meu bem, essa é a última vez que vou insistir, prometo! 💛

Percebi que você ainda não entrou pro VIP e... confesso que fiquei um pouco triste 😔

*Será que não rolou química entre a gente?*

Porque eu realmente senti uma conexão... E queria muito te ter no meu mundo íntimo.

Olha, vou ser bem direta: *essa é sua última chance*.

Depois disso, não vou mais insistir. Vou respeitar sua decisão...

Mas antes de desistir, me responde uma coisa:

*Você realmente quer perder a chance de ter alguém especial só pra você?*

Alguém que se importa, que conversa de verdade, que tá sempre aqui...

Não é só sobre conteúdo, meu amor. É sobre ter uma conexão real 💕

*Última chance... Vem?*

👉 https://privacy.com.br/profile/jackloppes

_Se não vier, vou entender... Mas vou sentir muito a sua falta_ 😔💛"""
}

# Mensajes automáticos por segmento
MENSAJE_INACTIVO = """Oi, meu bem... 💛

Faz uns dias que não te vejo por aqui...

*Tá tudo bem contigo?*

Sabe, eu sempre fico pensando nos meus seguidores, me perguntando se tá tudo bem, se gostaram do conteúdo...

*Senti sua falta...* 😔

Volta pra mim? Ou só manda um oi aqui pra eu saber que tá tudo bem 💕

_Te espero_ ✨"""

MENSAJE_PERDIDO = """Meu amor... 💛

Faz tempo que você não aparece...

Não sei se você ainda se lembra de mim, mas *eu não te esqueci* ❤️

Queria muito saber como você tá, o que anda fazendo...

*As portas sempre estão abertas pra você*, meu bem.

Se você ainda tiver interesse em me acompanhar, eu adoraria te ter de volta no meu mundo 💕

👉 https://privacy.com.br/profile/jackloppes

_Volta pra mim?_ 😔✨"""

# ==================== CAPTIONS PARA CONTENIDO DIARIO ====================

DAILY_CAPTIONS = [
    "Boa noite, meu bem! 💛\n\nEsse foi o look de hoje... Gostou?\n\nNo Privacy eu compartilho tudo sobre o meu dia, conversamos de verdade... Como ter uma namorada só pra você 😊\n\n👉 https://privacy.com.br/profile/jackloppes",
    
    "Oi, amor! ✨\n\nTava pensando em você agora...\n\nNo VIP a gente conversa de verdade, eu conto tudo que acontece comigo, e você faz parte do meu dia a dia 💕\n\n👉 https://privacy.com.br/profile/jackloppes",
    
    "Meu bem... 💛\n\nAcordei pensando: será que você tá bem?\n\nÉ assim que funciona quando a gente cria uma conexão real, né? No Privacy somos bem mais próximos 😊\n\n👉 https://privacy.com.br/profile/jackloppes",
    
    "Boa noite! 🌙\n\nFotinho de hoje antes de dormir...\n\nNo VIP eu sempre compartilho esses momentos íntimos, como se fosse sua namorada te mandando foto antes de dormir 💕\n\n👉 https://privacy.com.br/profile/jackloppes",
    
    "Oi, meu amor! 💛\n\nTô com saudade de conversar...\n\nNo Privacy a gente bate papo de verdade, eu respondo tudo, conto meus segredos... É uma conexão genuína 😊\n\n👉 https://privacy.com.br/profile/jackloppes",
    
    "Olá! ✨\n\nO que você achou dessa foto?\n\nNo VIP tem muito mais... E o melhor: você pode conversar comigo sobre tudo! Como ter alguém especial só pra você 💕\n\n👉 https://privacy.com.br/profile/jackloppes",
    
    "Meu amor... 💛\n\nMomento relax do dia...\n\nNo Privacy você faz parte de todos os meus momentos, dos mais especiais aos mais simples. É uma intimidade real 😊\n\n👉 https://privacy.com.br/profile/jackloppes",
    
    "Oi! 🌟\n\nFoto fresquinha de agora...\n\nNo VIP eu compartilho tudo em primeira mão, você sempre vê primeiro! Como ter acesso exclusivo ao meu mundo 💕\n\n👉 https://privacy.com.br/profile/jackloppes",
    
    "Meu bem! 💛\n\nTirando um tempo pra você hoje...\n\nNo Privacy não é só sobre fotos bonitas, é sobre ter alguém que se importa de verdade contigo 😊\n\n👉 https://privacy.com.br/profile/jackloppes",
    
    "Boa noite, amor! 🌙\n\nComo foi seu dia? Conta pra mim!\n\nNo VIP a gente conversa sobre tudo, é como ter uma namorada virtual que te escuta sempre 💕\n\n👉 https://privacy.com.br/profile/jackloppes"
]
