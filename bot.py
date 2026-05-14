import discord
from discord.ext import commands
import json, os, requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")
DATA_FILE = "data.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ── Data Helpers ──────────────────────────────────────────────────────────────

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"international": [], "indonesia": {}, "usd_cash": []}
    with open(DATA_FILE) as f:
        data = json.load(f)
    # migrate old dict-based international to list
    if isinstance(data.get("international"), dict):
        migrated = []
        for name, s in data["international"].items():
            s["name"] = name
            s["label"] = name
            migrated.append(s)
        data["international"] = migrated
    return data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ── API Helpers ───────────────────────────────────────────────────────────────

def get_usd_to_idr():
    try:
        r = requests.get(
            f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/USD",
            timeout=5
        )
        return r.json()["conversion_rates"]["IDR"]
    except Exception:
        return 16000

def get_stock_price(ticker: str):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        return round(float(price), 2)
    except Exception:
        return None

def fmt_idr(amount: float) -> str:
    return "Rp {:,.0f}".format(amount).replace(",", ".")

def fmt_usd(amount: float) -> str:
    return f"${amount:,.2f}"

def get_stock_count(data, name):
    return len([s for s in data["international"] if s["name"].lower() == name.lower()])

# ── Commands ──────────────────────────────────────────────────────────────────

@bot.command(name="addstock")
async def add_stock(ctx, name: str, ticker: str, bought_usd: float, buy_price: float):
    """
    Add a stock holding. Buying the same stock again creates a new entry (Google #1, Google #2).
    Usage: !addstock Google GOOGL 30 295.83
    """
    async with ctx.typing():
        current_price = get_stock_price(ticker)
        if current_price is None:
            return await ctx.send(f"❌ Could not fetch price for **{ticker}**. Check the ticker and try again.")

        rate = get_usd_to_idr()
        shares = round(bought_usd / buy_price, 4)
        total_usd = round(shares * current_price, 2)
        total_idr = round(total_usd * rate)

        data = load_data()
        count = get_stock_count(data, name)

        # if this is the first entry, label is just the name
        # if there are already entries, relabel existing one as #1 and new one as #2
        if count == 0:
            label = name
        else:
            # relabel existing single entry to #1 if needed
            if count == 1:
                for s in data["international"]:
                    if s["name"].lower() == name.lower():
                        s["label"] = f"{s['name']} #1"
            label = f"{name} #{count + 1}"

        entry = {
            "name": name,
            "label": label,
            "ticker": ticker.upper(),
            "first_buy_usd": bought_usd,
            "buy_price": buy_price,
            "current_price": current_price,
            "shares": shares,
            "total_usd": total_usd,
            "total_idr": total_idr,
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        data["international"].append(entry)
        save_data(data)

    await ctx.send(
        f"✅ **{label}** ({ticker.upper()}) added!\n"
        f"Shares : `{shares}` @ `${current_price}` (live)\n"
        f"Total  : **{fmt_usd(total_usd)}** | {fmt_idr(total_idr)}"
    )


@bot.command(name="editstock")
async def edit_stock(ctx, index: int, field: str, *, value: str):
    """
    Edit a stock entry by index number. Use !list to see index numbers.
    Usage: !editstock 1 buy_price 300
    Fields: ticker | bought_usd | buy_price
    """
    data = load_data()
    entries = data["international"]
    if index < 1 or index > len(entries):
        return await ctx.send(f"❌ Entry #{index} doesn't exist. Use `!list` to see all entries.")

    s = entries[index - 1]
    valid_fields = {"ticker", "bought_usd", "buy_price"}
    if field not in valid_fields:
        return await ctx.send(f"❌ Invalid field. Choose from: `ticker` `bought_usd` `buy_price`")

    try:
        if field == "ticker":
            s["ticker"] = value.upper()
        else:
            s[field] = float(value)
    except ValueError:
        return await ctx.send(f"❌ `{value}` is not a valid number.")

    async with ctx.typing():
        current_price = get_stock_price(s["ticker"])
        if current_price is None:
            return await ctx.send(f"❌ Could not fetch price for **{s['ticker']}**.")
        rate = get_usd_to_idr()
        s["shares"] = round(s["first_buy_usd"] / s["buy_price"], 4)
        s["current_price"] = current_price
        s["total_usd"] = round(s["shares"] * current_price, 2)
        s["total_idr"] = round(s["total_usd"] * rate)
        s["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_data(data)

    await ctx.send(f"✏️ **{s['label']}** updated! `{field}` → `{value}`\nRecalculated: **{fmt_usd(s['total_usd'])}** | {fmt_idr(s['total_idr'])}")


@bot.command(name="deletestock")
async def delete_stock(ctx, index: int):
    """
    Remove a stock entry by index number. Use !list to see index numbers.
    Usage: !deletestock 1
    """
    data = load_data()
    entries = data["international"]
    if index < 1 or index > len(entries):
        return await ctx.send(f"❌ Entry #{index} doesn't exist. Use `!list` to see all entries.")

    removed = entries.pop(index - 1)

    # re-label remaining entries of the same stock name
    same = [s for s in data["international"] if s["name"].lower() == removed["name"].lower()]
    if len(same) == 1:
        same[0]["label"] = same[0]["name"]
    elif len(same) > 1:
        for i, s in enumerate(same, 1):
            s["label"] = f"{s['name']} #{i}"

    save_data(data)
    await ctx.send(f"🗑️ **{removed['label']}** removed.")


@bot.command(name="addusd")
async def add_usd(ctx, idr_amount: float, buy_rate: float):
    """
    Add IDR cash that was converted to USD.
    Usage: !addusd 1000000 17400
    """
    async with ctx.typing():
        current_rate = get_usd_to_idr()
        usd_value = round(idr_amount / buy_rate, 2)
        current_idr = round(usd_value * current_rate)

    data = load_data()
    data["usd_cash"].append({
        "idr_deposited": idr_amount,
        "buy_rate": buy_rate,
        "current_rate": current_rate,
        "usd_value": usd_value,
        "current_idr": current_idr,
        "date": datetime.now().strftime("%Y-%m-%d"),
    })
    save_data(data)
    await ctx.send(
        f"💵 USD Cash added!\n"
        f"{fmt_idr(idr_amount)} @ {buy_rate:,.0f} = **{fmt_usd(usd_value)}**\n"
        f"Current value: {fmt_idr(current_idr)} (rate: {current_rate:,.0f})"
    )


@bot.command(name="editusd")
async def edit_usd(ctx, index: int, field: str, value: float):
    """
    Edit a USD cash entry by index. Use !list to see index numbers.
    Usage: !editusd 1 idr_deposited 1200000
    Fields: idr_deposited | buy_rate
    """
    data = load_data()
    entries = data.get("usd_cash", [])
    if index < 1 or index > len(entries):
        return await ctx.send(f"❌ Entry #{index} doesn't exist.")
    valid = {"idr_deposited", "buy_rate"}
    if field not in valid:
        return await ctx.send(f"❌ Invalid field. Choose: `idr_deposited` or `buy_rate`")

    e = entries[index - 1]
    e[field] = value
    async with ctx.typing():
        current_rate = get_usd_to_idr()
        e["usd_value"] = round(e["idr_deposited"] / e["buy_rate"], 2)
        e["current_rate"] = current_rate
        e["current_idr"] = round(e["usd_value"] * current_rate)
    save_data(data)
    await ctx.send(f"✏️ USD Cash entry #{index} updated. New value: **{fmt_usd(e['usd_value'])}** | {fmt_idr(e['current_idr'])}")


@bot.command(name="deleteusd")
async def delete_usd(ctx, index: int):
    """
    Remove a USD cash entry by index. Use !list to see index numbers.
    Usage: !deleteusd 1
    """
    data = load_data()
    entries = data.get("usd_cash", [])
    if index < 1 or index > len(entries):
        return await ctx.send(f"❌ Entry #{index} doesn't exist.")
    removed = entries.pop(index - 1)
    save_data(data)
    await ctx.send(f"🗑️ USD Cash entry #{index} ({fmt_idr(removed['idr_deposited'])}) removed.")


@bot.command(name="addidr")
async def add_idr(ctx, name: str, balance: float, *, location: str):
    """
    Add an Indonesian savings or reksadana account (IDR only).
    Usage: !addidr RDN 1251000 Mandiri
           !addidr Reksadana 500000 Bibit
    """
    data = load_data()
    data["indonesia"][name] = {"balance": balance, "location": location}
    save_data(data)
    await ctx.send(f"✅ **{name}** saved: {fmt_idr(balance)} @ {location}")


@bot.command(name="editidr")
async def edit_idr(ctx, name: str, field: str, *, value: str):
    """
    Edit an Indonesia savings entry.
    Usage: !editidr RDN balance 1500000
           !editidr RDN location BCA
    Fields: balance | location
    """
    data = load_data()
    if name not in data["indonesia"]:
        return await ctx.send(f"❌ **{name}** not found. Use `!list` to see all entries.")
    valid = {"balance", "location"}
    if field not in valid:
        return await ctx.send(f"❌ Invalid field. Choose: `balance` or `location`")
    if field == "balance":
        try:
            data["indonesia"][name]["balance"] = float(value)
        except ValueError:
            return await ctx.send(f"❌ `{value}` is not a valid number.")
    else:
        data["indonesia"][name]["location"] = value
    save_data(data)
    await ctx.send(f"✏️ **{name}** updated. `{field}` → `{value}`")


@bot.command(name="deleteidr")
async def delete_idr(ctx, *, name: str):
    """
    Remove an Indonesia savings entry.
    Usage: !deleteidr RDN
    """
    data = load_data()
    if name not in data["indonesia"]:
        return await ctx.send(f"❌ **{name}** not found.")
    del data["indonesia"][name]
    save_data(data)
    await ctx.send(f"🗑️ **{name}** removed.")


@bot.command(name="refresh")
async def refresh(ctx):
    """
    Refresh all stock prices and exchange rate from live APIs.
    Usage: !refresh
    """
    data = load_data()
    async with ctx.typing():
        rate = get_usd_to_idr()
        updated = []
        failed = []
        for s in data["international"]:
            price = get_stock_price(s["ticker"])
            if price is None:
                failed.append(s["label"])
                continue
            s["current_price"] = price
            s["total_usd"] = round(s["shares"] * price, 2)
            s["total_idr"] = round(s["total_usd"] * rate)
            s["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            updated.append(f"**{s['label']}** ({s['ticker']}) → ${price}")

        for e in data.get("usd_cash", []):
            e["current_rate"] = rate
            e["current_idr"] = round(e["usd_value"] * rate)

        save_data(data)

    msg = f"🔄 Refreshed! Rate: `{rate:,.0f} IDR/USD`\n"
    if updated:
        msg += "\n".join(updated)
    if failed:
        msg += f"\n⚠️ Failed to fetch: {', '.join(failed)}"
    await ctx.send(msg)


@bot.command(name="summary")
async def summary(ctx):
    """
    Show your full monthly savings summary.
    Usage: !summary
    """
    async with ctx.typing():
        data = load_data()
        rate = get_usd_to_idr()
        month = datetime.now().strftime("%B %Y").upper()
        date = datetime.now().strftime("%d %B %Y")

        lines = [
            f"**📊 MONTHLY CHECK-IN : {month}**",
            f"📅 {date}\n",
            "**🌍 INTERNATIONAL STOCKS**\n"
        ]

        total_usd = 0.0
        total_idr_intl = 0

        for s in data["international"]:
            total_usd += s["total_usd"]
            total_idr_intl += s["total_idr"]
            lines.append(
                f"**{s['label']}**\n"
                f"First Buy : {fmt_usd(s['first_buy_usd'])} @ ${s['buy_price']:,.2f}  "
                f"NOW : ${s['current_price']:,.2f}\n"
                f"Shares : {s['shares']}  "
                f"Total : **{fmt_usd(s['total_usd'])}**  "
                f"Total IDR : {fmt_idr(s['total_idr'])}\n"
            )

        usd_cash_entries = data.get("usd_cash", [])
        if usd_cash_entries:
            usd_cash_total = sum(e["usd_value"] for e in usd_cash_entries)
            usd_cash_idr = sum(e["current_idr"] for e in usd_cash_entries)
            total_usd += usd_cash_total
            total_idr_intl += usd_cash_idr

            if len(usd_cash_entries) == 1:
                e = usd_cash_entries[0]
                lines.append(
                    f"**USD Cash**\n"
                    f"First Buy : {fmt_idr(e['idr_deposited'])} @ {e['buy_rate']:,.0f}  "
                    f"NOW : {e['current_rate']:,.0f}\n"
                    f"Total : **{fmt_usd(e['usd_value'])}**  "
                    f"Total IDR : {fmt_idr(e['current_idr'])}\n"
                )
            else:
                lines.append(
                    f"**USD Cash** ({len(usd_cash_entries)} entries)\n"
                    f"Total : **{fmt_usd(usd_cash_total)}**  "
                    f"Total IDR : {fmt_idr(usd_cash_idr)}\n"
                )

        lines.append("──────────────────────")
        lines.append("**🇮🇩 INDONESIA**\n")

        total_idr_id = 0
        for name, s in data["indonesia"].items():
            total_idr_id += s["balance"]
            lines.append(f"**{name}**\nBalance : {fmt_idr(s['balance'])}  Location : {s['location']}\n")

        grand_total = total_idr_intl + total_idr_id

        lines.append("──────────────────────")
        lines.append(
            f"**SUMMARY**\n"
            f"Total USD : **{fmt_usd(total_usd)}**\n"
            f"Total IDR (Intl) : {fmt_idr(total_idr_intl)}\n"
            f"Total IDR (ID)   : {fmt_idr(total_idr_id)}\n"
            f"**Grand Total IDR : {fmt_idr(grand_total)}**\n"
            f"*(Rate: {rate:,.0f} IDR/USD)*"
        )

    await ctx.send("\n".join(lines))


@bot.command(name="list")
async def list_entries(ctx):
    """
    List all saved entries with index numbers.
    Usage: !list
    """
    data = load_data()
    lines = ["**📋 All Saved Entries**\n"]

    lines.append("**🌍 International Stocks**")
    if data["international"]:
        for i, s in enumerate(data["international"], 1):
            lines.append(f"  `#{i}` {s['label']} ({s['ticker']}) — {fmt_usd(s['total_usd'])}")
    else:
        lines.append("  *(none)*")

    lines.append("\n**💵 USD Cash**")
    if data.get("usd_cash"):
        for i, e in enumerate(data["usd_cash"], 1):
            lines.append(f"  `#{i}` {fmt_idr(e['idr_deposited'])} deposited on {e['date']} — {fmt_usd(e['usd_value'])}")
    else:
        lines.append("  *(none)*")

    lines.append("\n**🇮🇩 Indonesia**")
    if data["indonesia"]:
        for name, s in data["indonesia"].items():
            lines.append(f"  • {name} — {fmt_idr(s['balance'])} ({s['location']})")
    else:
        lines.append("  *(none)*")

    await ctx.send("\n".join(lines))


@bot.command(name="tutorial")
async def tutorial(ctx):
    """Show a full tutorial on how to use ChoubaWealth."""
    msg = """**📖 ChoubaWealth — Full Tutorial**

**━━━ ADDING YOUR HOLDINGS ━━━**

🌍 **International Stock**
`!addstock <name> <ticker> <spent_usd> <buy_price>`
Example: `!addstock Google GOOGL 30 295.83`
→ Buying Google again later at a different price?
Just run it again → saves as **Google #1** and **Google #2**

💵 **USD Cash (IDR converted to USD)**
`!addusd <idr_amount> <buy_rate>`
Example: `!addusd 1000000 17400`

🇮🇩 **Indonesia Savings / Reksadana (IDR only)**
`!addidr <name> <balance> <location>`
Example: `!addidr RDN 1251000 Mandiri`
Example: `!addidr Reksadana 500000 Bibit`
Example: `!addidr Tabungan 500000 Mandiri`

**━━━ EDITING ━━━**
Run `!list` first to get the `#` index number

✏️ **Edit a stock** (use index from !list)
`!editstock <#> <field> <value>`
Fields: `ticker` `bought_usd` `buy_price`
Example: `!editstock 1 buy_price 300`

✏️ **Edit USD Cash** (use index from !list)
`!editusd <#> <field> <value>`
Fields: `idr_deposited` `buy_rate`
Example: `!editusd 1 buy_rate 17500`

✏️ **Edit Indonesia entry**
`!editidr <name> <field> <value>`
Fields: `balance` `location`
Example: `!editidr RDN balance 1500000`

**━━━ DELETING ━━━**
`!deletestock <#>` — use index from !list
`!deleteusd <#>` — use index from !list
`!deleteidr <name>` — use the name directly

**━━━ MONTHLY ROUTINE ━━━**
1️⃣ `!refresh` — fetch latest prices & exchange rate
2️⃣ `!summary` — view your full monthly check-in
3️⃣ Screenshot and done ✅

**━━━ OTHER ━━━**
`!list` — see all entries with index numbers
`!w` — quick command reference
`!tutorial` — show this guide
"""
    await ctx.send(msg)


@bot.command(name="w")
async def wealth_help(ctx):
    """Quick command reference."""
    help_text = """**💰 ChoubaWealth — Commands**

`!addstock <name> <ticker> <spent_usd> <buy_price>`
`!editstock <#> <field> <value>` — fields: `ticker` `bought_usd` `buy_price`
`!deletestock <#>`

`!addusd <idr_amount> <buy_rate>`
`!editusd <#> <field> <value>` — fields: `idr_deposited` `buy_rate`
`!deleteusd <#>`

`!addidr <name> <balance> <location>`
`!editidr <name> <field> <value>` — fields: `balance` `location`
`!deleteidr <name>`

`!refresh` — update all prices & exchange rate
`!summary` — full monthly check-in
`!list` — see all entries + index numbers
`!tutorial` — full guide
`!w` — this message
"""
    await ctx.send(help_text)


@bot.event
async def on_ready():
    print(f"✅ ChoubaWealth online as {bot.user}")

bot.run(TOKEN)