# 🎬 پیشنهاد فیلم (Movie Suggestion) — Telegram Bot

ربات تلگرام دوزبانه (فارسی/انگلیسی) برای پیشنهاد فیلم و سریال بر اساس امتیاز
IMDb، Rotten Tomatoes، Metacritic، ژانر، حال‌وهوا و تیپ شخصیتی (MBTI).

A bilingual (Persian/English) Telegram bot for movie & series recommendations,
combining IMDb / Rotten Tomatoes / Metacritic ratings with genre, mood, and
MBTI personality type.

---

## ⚠️ Please read first — two important, honest notes

**۱) توکن ربات شما.** توکنی که در چت فرستادید در فایل `.env.example`
گذاشته شده تا بلافاصله تست کنید. اما چون این توکن داخل یک مکالمه فرستاده
شده، به‌عنوان یک عادت امنیتی خوب توصیه می‌کنم از طریق @BotFather با دستور
`/revoke` آن را باطل و یک توکن جدید بگیرید، سپس توکن جدید را در `.env`
جایگزین کنید. این کار فقط چند ثانیه طول می‌کشد.

**Your bot token.** The token you shared is already placed in `.env.example`
so you can test immediately. However, since it was sent in a chat, as good
security hygiene I'd recommend revoking it via @BotFather (`/revoke`) and
generating a fresh one, then swapping it into `.env`. Takes seconds.

**۲) درباره «بدون هیچ API key» و «۱۰۰۰ عامل».** این ربات کاملاً و بلافاصله
کار می‌کند — چون یک دیتاست منتخب (حدود ۱۲۰ فیلم/سریال برتر + فهرست ژانرها +
چند بازیگر/کارگردان مشهور + فیلم‌های در انتظار اکران) از قبل داخلش قرار
دارد. اما **دریافت واقعی و زنده‌ی امتیاز از IMDb/RT/Metacritic برای *هر*
فیلمی، یا جست‌وجوی *هر* بازیگر/کارگردانی**، فنی و قانونی فقط با یک API
(نه اسکرپینگ سایت‌هایی مثل IMDb که این کار را ممنوع می‌کنند) ممکن است. دو
سرویس رایگان و بدون نیاز به کارت اعتباری برای این کار هست: OMDb و TMDb —
هر دو دو دقیقه‌ای ثبت‌نام می‌شوند. من نمی‌توانم برای شما ثبت‌نام کنم چون
نیاز به ایمیل/حساب شخصی شماست، اما ربات کاملاً طوری نوشته شده که با یا
بدون آن‌ها کار می‌کند. همچنین «۱۰۰۰ عامل» به‌صورت یک موتور امتیازدهی
شفاف و چندعاملی (ژانر، حال‌وهوا، MBTI، فیلم‌های موردعلاقه/منفور) پیاده‌سازی
شده — نه یک مدل یادگیری ماشین با هزار پارامتر واقعی، چون آن نیاز به
دیتاست آموزشی و زیرساخت جداگانه‌ای دارد که در حد یک ربات تلگرام نیست.

**On "no API keys" and "1000 factors."** The bot works fully and
immediately because it ships with a curated dataset (~120 top movies/
series, genre lists, a handful of well-known actors/directors, and an
upcoming-releases list). But getting *live* ratings for *any* movie from
IMDb/RT/Metacritic, or searching *any* actor/director, technically and
legally requires an API (not scraping IMDb directly — their terms forbid
it). Two free services with no credit card needed handle this: **OMDb**
and **TMDb**, each a 2-minute signup. I can't sign up on your behalf since
it needs your own email/account, but the bot is written to work great with
or without them. Also, "1,000 factors" is implemented honestly as a
transparent, multi-signal scoring engine (genre + mood + MBTI + liked/
disliked overlap) — not a literal machine-learning model with a thousand
trained parameters, since that would need its own training dataset and
infrastructure well beyond a Telegram bot.

Bottom line: **it works right now, out of the box.** Adding the two free
keys below just upgrades "curated dataset" → "live, unlimited data."

---

## ✅ What's included

| Feature | Fa | En | Works without API keys? |
|---|---|---|---|
| IMDb-rated Top list (40 shown, dataset has 120) | ۲۵۰ فیلم/سریال برتر IMDb | IMDb Top | ✅ Yes (curated snapshot) |
| Top by genre (Romance, Drama, Comedy, Action, Sci-Fi, Horror) | برترین‌های هر ژانر | Top by Genre | ✅ Yes |
| Actor search → top 10 credits | جست‌وجوی بازیگر | Search Actor | ✅ for 6 sample actors, ✅ unlimited with TMDB_API_KEY |
| Director search → top 10 credits | جست‌وجوی کارگردان | Search Director | ✅ for 6 sample directors, ✅ unlimited with TMDB_API_KEY |
| Upcoming/most-anticipated releases | در انتظار اکران | Upcoming Releases | ✅ static list, ✅ live with TMDB_API_KEY |
| Compare a movie's IMDb/RT/Metacritic ratings | مقایسه امتیاز یک فیلم | Compare Ratings | ✅ for dataset titles, ✅ unlimited with OMDB_API_KEY |
| Smart quiz (mood + genre + MBTI + liked/disliked) → personalized picks | پیشنهاد هوشمند اختصاصی | Smart Personal Pick | ✅ Yes, fully offline |
| Persian / English toggle, anytime | تغییر زبان | Change Language | ✅ Yes |

---

## 🚀 How to run it

1. **Install Python 3.10+**, then in this folder:
   ```bash
   pip install -r requirements.txt
   ```
2. **Copy `.env.example` to `.env`** and make sure `BOT_TOKEN` is set
   (see the security note above about regenerating it).
3. *(Optional but recommended)* Get free keys and paste them into `.env`:
   - OMDb: http://www.omdbapi.com/apikey.aspx
   - TMDb: https://www.themoviedb.org/settings/api
4. **Run it:**
   ```bash
   python bot.py
   ```
5. Open Telegram, find your bot, send `/start`.

### Deploying so it runs 24/7
Running `python bot.py` on your own laptop only works while your laptop is
on. For 24/7 uptime, run it on a small always-on server — e.g. a free-tier
VM, a $4–5/month VPS (Hetzner, DigitalOcean, etc.), or a container platform
like Railway/Fly.io. Any of them: upload this folder, install
requirements, set the `.env` values, and run `python bot.py` (ideally under
`systemd`, `pm2`, or `tmux` so it restarts if it crashes).

---

## 🗂️ Project structure

```
moviebot/
├── bot.py              # main bot: handlers, FSM quiz, menu logic
├── recommender.py       # the weighted scoring engine
├── keyboards.py          # inline "button box" keyboards
├── locales.py             # all fa/en text strings
├── data/
│   ├── imdb_top.py        # curated top ~120 movies & series
│   ├── genre_extra.py      # extra titles per genre
│   ├── people.py            # sample actor/director filmographies
│   └── upcoming.py           # anticipated upcoming releases
├── requirements.txt
├── .env.example
└── README.md (this file)
```

## 🧠 How the "smart recommendation" works

The bot asks: mood → favorite genre → MBTI type (optional) → movies you
liked → movies you disliked. It then scores every title in the dataset by:
- base quality (average of normalized IMDb/RT/Metacritic scores),
- genre match with your stated preference,
- genre affinity implied by your mood,
- a simplified, for-fun MBTI→genre heuristic (not a validated psychological
  claim),
- a boost for genres shared with movies you loved, and a penalty for genres
  shared with movies you disliked,
- then removes anything you named as disliked outright.

This is transparent and tunable (see `MOOD_GENRE_WEIGHTS` and
`MBTI_GENRE_WEIGHTS` in `recommender.py`) — feel free to adjust the
weights to your own taste.

## 🎨 About the "glass box" buttons
Telegram bot chats render with Telegram's own native theme — a bot cannot
inject custom CSS/glassmorphism into a normal chat message. What this
project uses instead is Telegram's inline keyboards, grouped tightly under
each message, which Telegram's client already renders with soft rounded
corners and a translucent tap-highlight (this is the closest "glass panel"
look achievable in a standard bot chat). If you want a literal
glassmorphism UI, that requires a **Telegram Mini App / Web App**
(a real HTML/CSS/JS page opened inside Telegram) — a bigger project than a
chat bot; ask if you'd like a starter for that too.

## 📌 Extending the dataset
All movie/genre/people/upcoming data lives in plain Python lists/dicts
under `data/`. Add more rows in the same tuple format to expand any
section — no code changes needed elsewhere.
