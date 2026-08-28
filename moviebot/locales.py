"""All user-facing text, in Persian (fa) and English (en)."""

TXT = {
    "choose_lang": {
        "fa": "🌐 لطفاً زبان را انتخاب کنید / Please choose a language:",
        "en": "🌐 Please choose a language / لطفاً زبان را انتخاب کنید:",
    },
    "welcome": {
        "fa": (
            "🎬 <b>به «پیشنهاد فیلم» خوش آمدید!</b>\n\n"
            "من به شما کمک می‌کنم بهترین فیلم‌ها و سریال‌ها را بر اساس امتیاز "
            "IMDb، Rotten Tomatoes، Metacritic و همچنین سلیقه، حال‌وهوا، "
            "ژانر و حتی تیپ شخصیتی (MBTI) شما پیدا کنید.\n\n"
            "یکی از گزینه‌های زیر را انتخاب کنید 👇"
        ),
        "en": (
            "🎬 <b>Welcome to Movie Suggestion!</b>\n\n"
            "I help you find the best movies and shows by combining "
            "IMDb, Rotten Tomatoes, Metacritic scores with your taste, "
            "mood, genre preferences, and even your MBTI personality type.\n\n"
            "Choose an option below 👇"
        ),
    },
    "menu_top250": {"fa": "🏆 ۲۵۰ فیلم/سریال برتر IMDb", "en": "🏆 IMDb Top 250"},
    "menu_genre": {"fa": "🎭 برترین‌های هر ژانر", "en": "🎭 Top by Genre"},
    "menu_actor": {"fa": "🎭 جست‌وجوی بازیگر", "en": "🎭 Search Actor"},
    "menu_director": {"fa": "🎬 جست‌وجوی کارگردان", "en": "🎬 Search Director"},
    "menu_upcoming": {"fa": "📅 در انتظار اکران", "en": "📅 Upcoming Releases"},
    "menu_recommend": {"fa": "🤖 پیشنهاد هوشمند اختصاصی", "en": "🤖 Smart Personal Pick"},
    "menu_compare": {"fa": "⚖️ مقایسه امتیاز یک فیلم", "en": "⚖️ Compare a Movie's Ratings"},
    "menu_lang": {"fa": "🌐 تغییر زبان", "en": "🌐 Change Language"},
    "back": {"fa": "🔙 بازگشت", "en": "🔙 Back"},
    "genre_romance": {"fa": "❤️ عاشقانه", "en": "❤️ Romance"},
    "genre_drama": {"fa": "🎭 درام", "en": "🎭 Drama"},
    "genre_comedy": {"fa": "😂 کمدی", "en": "😂 Comedy"},
    "genre_action": {"fa": "💥 اکشن", "en": "💥 Action"},
    "genre_scifi": {"fa": "🚀 علمی‌تخیلی", "en": "🚀 Sci-Fi"},
    "genre_horror": {"fa": "👻 ترسناک", "en": "👻 Horror"},
    "pick_genre": {"fa": "یک ژانر را انتخاب کنید:", "en": "Pick a genre:"},
    "ask_actor_name": {
        "fa": "✍️ نام بازیگر مورد نظر را بنویسید (مثلاً: Leonardo DiCaprio):",
        "en": "✍️ Type the actor's name (e.g. Leonardo DiCaprio):",
    },
    "ask_director_name": {
        "fa": "✍️ نام کارگردان مورد نظر را بنویسید (مثلاً: Christopher Nolan):",
        "en": "✍️ Type the director's name (e.g. Christopher Nolan):",
    },
    "ask_movie_name": {
        "fa": "✍️ نام فیلم یا سریالی که می‌خواهید امتیازش را مقایسه کنید بنویسید:",
        "en": "✍️ Type the movie or show title you want ratings for:",
    },
    "not_found_local": {
        "fa": (
            "😕 این مورد در دیتابیس داخلی من نبود.\n"
            "برای جست‌وجوی نامحدود (هر بازیگر/کارگردان/فیلمی)، یک کلید رایگان "
            "TMDb یا OMDb به فایل .env اضافه کنید — در README توضیح داده شده."
        ),
        "en": (
            "😕 That wasn't in my built-in database.\n"
            "For unlimited search (any actor/director/movie), add a free "
            "TMDb or OMDb key to your .env file — explained in the README."
        ),
    },
    "start_quiz": {
        "fa": (
            "🤖 بسیار خب! چند سؤال کوتاه می‌پرسم تا پیشنهاد دقیق و شخصی‌سازی‌شده بدهم.\n"
            "می‌توانید هر زمان با /cancel لغو کنید."
        ),
        "en": (
            "🤖 Great! I'll ask a few quick questions to tailor a precise, "
            "personal recommendation.\nYou can cancel anytime with /cancel."
        ),
    },
    "q_mood": {
        "fa": "1️⃣ الان چه حال‌وهوایی دارید؟",
        "en": "1️⃣ What's your mood right now?",
    },
    "mood_happy": {"fa": "😄 شاد / سرگرم‌کننده", "en": "😄 Fun / Upbeat"},
    "mood_thoughtful": {"fa": "🤔 فکر برانگیز", "en": "🤔 Thought-provoking"},
    "mood_relax": {"fa": "😌 آرامش‌بخش", "en": "😌 Relaxing"},
    "mood_intense": {"fa": "🔥 پرهیجان / پرتنش", "en": "🔥 Intense"},
    "mood_sad": {"fa": "😢 احساسی / غم‌انگیز", "en": "😢 Emotional / Sad"},
    "q_genre": {
        "fa": "2️⃣ کدام ژانر را بیشتر ترجیح می‌دهید؟",
        "en": "2️⃣ Which genre do you lean toward most?",
    },
    "q_mbti": {
        "fa": (
            "3️⃣ تیپ شخصیتی MBTI شما چیست؟ (اگر نمی‌دانید «نمی‌دانم» را بزنید)"
        ),
        "en": (
            "3️⃣ What's your MBTI personality type? (tap \"I don't know\" if unsure)"
        ),
    },
    "mbti_unknown": {"fa": "🤷 نمی‌دانم / رد شو", "en": "🤷 I don't know / Skip"},
    "q_liked": {
        "fa": (
            "4️⃣ نام ۱ تا ۳ فیلم یا سریالی که واقعاً دوست داشتید را بنویسید "
            "(با کاما جدا کنید)، یا برای رد شدن «-» بفرستید:"
        ),
        "en": (
            "4️⃣ Name 1-3 movies/shows you truly loved (comma-separated), "
            "or send \"-\" to skip:"
        ),
    },
    "q_disliked": {
        "fa": (
            "5️⃣ حالا ۱ تا ۳ فیلم یا سریالی که دوست نداشتید بنویسید "
            "(با کاما جدا کنید)، یا برای رد شدن «-» بفرستید:"
        ),
        "en": (
            "5️⃣ Now name 1-3 movies/shows you disliked (comma-separated), "
            "or send \"-\" to skip:"
        ),
    },
    "analyzing": {
        "fa": "🧠 در حال تحلیل سلیقه شما و مقایسه دیتابیس... چند لحظه صبر کنید ⏳",
        "en": "🧠 Analyzing your taste and cross-checking the database... ⏳",
    },
    "recommend_header": {
        "fa": "✅ <b>بر اساس تحلیل پاسخ‌های شما، این پیشنهادها را دارم:</b>\n",
        "en": "✅ <b>Based on your answers, here's what I recommend:</b>\n",
    },
    "cancelled": {"fa": "❌ لغو شد.", "en": "❌ Cancelled."},
    "compare_header": {
        "fa": "⚖️ <b>مقایسه امتیازها برای «{title}»</b>\n",
        "en": "⚖️ <b>Rating comparison for \"{title}\"</b>\n",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    s = TXT.get(key, {}).get(lang, TXT.get(key, {}).get("en", key))
    return s.format(**kwargs) if kwargs else s
