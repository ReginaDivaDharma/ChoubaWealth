# ChoubaWealth Discord Bot

A Discord bot for tracking stocks and savings. Basically monitors international stocks with live prices, converts USD to IDR automatically, and summarizes everything in a clean monthly check-in. 

𓆝 𓆟 𓆞 𓆝 𓆟

## Features

🧸ྀི Track international stocks with live prices from Yahoo Finance
🧸ྀི Track USD cash (converted from IDR)
🧸ྀི Track Indonesian savings & reksadana (IDR only) but this is still manual insert, not API based yet
🧸ྀི Auto-converts USD → IDR using live exchange rates
🧸ྀི One command monthly summary (`!summary`)

𓆝 𓆟 𓆞 𓆝 𓆟

## Tech Stack

- **Python** + **discord.py**
- **Yahoo Finance** — live stock prices (no API key needed)
- **ExchangeRate-API** — live USD/IDR conversion

𓆝 𓆟 𓆞 𓆝 𓆟

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/ReginaDivaDharma/ChoubaWealth.git
cd ChoubaWealth
```

### 2. Install dependencies
```bash
pip install discord.py python-dotenv requests
```

### 3. Create a `.env` file
```
DISCORD_TOKEN=your_discord_bot_token
EXCHANGE_RATE_API_KEY=your_exchangerate_api_key
```

- Get your Discord bot token at [discord.com/developers](https://discord.com/developers/applications)
- Get your free exchange rate key at [exchangerate-api.com](https://www.exchangerate-api.com)

### 4. Run the bot
```bash
python bot.py
```

### IMPORTANT NOTE
please do note this bot is still running locally

𓆝 𓆟 𓆞 𓆝 𓆟

## Commands

### Adding Holdings
| Command | Description |
|---|---|
| `!addstock <name> <ticker> <spent_usd> <buy_price>` | Add an international stock |
| `!addusd <idr_amount> <buy_rate>` | Add IDR cash converted to USD |
| `!addidr <name> <balance> <location>` | Add Indonesian savings or reksadana |

### Editing
| Command | Description |
|---|---|
| `!editstock <#> <field> <value>` | Edit a stock (fields: `ticker` `bought_usd` `buy_price`) |
| `!editusd <#> <field> <value>` | Edit USD cash (fields: `idr_deposited` `buy_rate`) |
| `!editidr <name> <field> <value>` | Edit IDR entry (fields: `balance` `location`) |

### Deleting
| Command | Description |
|---|---|
| `!deletestock <#>` | Remove a stock by index |
| `!deleteusd <#>` | Remove a USD cash entry by index |
| `!deleteidr <name>` | Remove an IDR entry by name |

### General
| Command | Description |
|---|---|
| `!refresh` | Fetch latest prices & exchange rate |
| `!summary` | Full monthly check-in |
| `!list` | See all entries with index numbers |
| `!tutorial` | Full usage guide |
| `!w` | Quick command reference |

𓆝 𓆟 𓆞 𓆝 𓆟

## Notes

- The bot runs **locally** — just keep the terminal open while using it
- `data.json` is auto-created on first use and stores all your data
- Never commit `.env` or `data.json` to GitHub
