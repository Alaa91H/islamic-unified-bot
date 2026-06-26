from bot.decorators import safe_handler


def register(app, deps) -> None:
    from pyrogram import filters
    from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

    from bot.data.hadith_data import HADITH_BOOKS, format_hadith, get_hadith

    @app.on_message(filters.private & filters.command("hadith"))
    @safe_handler()
    async def hadith_cmd(client, message):
        buttons = []
        for key, info in HADITH_BOOKS.items():
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"📚 {info['name']} ({info['total']:,})",
                        callback_data=f"hadith:book:{key}:1",
                    )
                ]
            )
        buttons.append([InlineKeyboardButton("🔍 بحث", callback_data="hadith:search")])
        buttons.append(
            [InlineKeyboardButton("🔙 الرئيسية", callback_data="back_to_start")]
        )

        await message.reply_text(
            "📚 **مكتبة الحديث الشريف**\n───\nاختر كتاباً لقراءة الأحاديث:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    @app.on_callback_query(filters.regex("^hadith:"))
    @safe_handler()
    async def hadith_callback(client, cq: CallbackQuery):
        parts = cq.data.split(":")
        action = parts[1]

        if action == "book":
            book = parts[2]
            page = int(parts[3]) if len(parts) > 3 else 1
            info = HADITH_BOOKS.get(book)
            if not info:
                await cq.answer("❌ كتاب غير معروف")
                return

            start = (page - 1) * 10 + 1
            end = min(start + 9, info["total"])

            lines = [f"📚 **{info['name']}**\n───\nأحاديث {start}-{end}:\n"]
            for i in range(start, end + 1):
                lines.append(f"• [{i}] اضغط لعرض الحديث → `/hadith {book} {i}`")

            nav = []
            if page > 1:
                nav.append(
                    InlineKeyboardButton(
                        "⬅️", callback_data=f"hadith:book:{book}:{page - 1}"
                    )
                )
            nav.append(
                InlineKeyboardButton(
                    f"{page}/{(info['total'] + 9) // 10}", callback_data="hadith:_"
                )
            )
            if end < info["total"]:
                nav.append(
                    InlineKeyboardButton(
                        "➡️", callback_data=f"hadith:book:{book}:{page + 1}"
                    )
                )

            buttons = [nav] if nav else []
            buttons.append(
                [InlineKeyboardButton("🔙 الكتب", callback_data="hadith:books")]
            )
            buttons.append(
                [InlineKeyboardButton("🔙 الرئيسية", callback_data="back_to_start")]
            )

            await cq.message.edit_text(
                "\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons)
            )
            await cq.answer()

        elif action == "books":
            buttons = []
            for key, info in HADITH_BOOKS.items():
                buttons.append(
                    [
                        InlineKeyboardButton(
                            f"📚 {info['name']} ({info['total']:,})",
                            callback_data=f"hadith:book:{key}:1",
                        )
                    ]
                )
            buttons.append(
                [InlineKeyboardButton("🔍 بحث", callback_data="hadith:search")]
            )
            buttons.append(
                [InlineKeyboardButton("🔙 الرئيسية", callback_data="back_to_start")]
            )
            await cq.message.edit_text(
                "📚 **مكتبة الحديث الشريف**\n───\nاختر كتاباً:",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            await cq.answer()

        elif action == "get":
            book = parts[2]
            number = int(parts[3])
            hadith = await get_hadith(book, number)
            if not hadith:
                await cq.answer("❌ لم يتم العثور على الحديث")
                return

            text = format_hadith(hadith)
            info = HADITH_BOOKS.get(book, {})
            buttons = [
                [
                    InlineKeyboardButton(
                        "⬅️ السابق", callback_data=f"hadith:get:{book}:{number - 1}"
                    )
                    if number > 1
                    else None,
                    InlineKeyboardButton(
                        "التالي ➡️", callback_data=f"hadith:get:{book}:{number + 1}"
                    )
                    if number < (info.get("total", 0))
                    else None,
                ],
                [
                    InlineKeyboardButton(
                        f"🔙 {info.get('name', '')}",
                        callback_data=f"hadith:book:{book}:{(number - 1) // 10 + 1}",
                    )
                ],
                [InlineKeyboardButton("🔙 الكتب", callback_data="hadith:books")],
            ]
            buttons = [[b for b in row if b] for row in buttons if any(b for b in row)]
            await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
            await cq.answer()

        elif action == "search":
            from pyrogram import filters as pf

            try:
                answer = await client.ask(
                    cq.message.chat.id,
                    "🔍 أرسل الكلمة أو الموضوع الذي تبحث عنه في الحديث:",
                    timeout=60,
                    filters=pf.text,
                )
            except TimeoutError:
                await cq.message.reply_text("❌ انتهت المهلة")
                return

            keyword = answer.text.strip()
            if not keyword:
                await answer.reply_text("❌ الرجاء إرسال كلمة للبحث")
                return

            await answer.reply_text(f"🔍 جاري البحث عن «{keyword}»...")

            from bot.data.hadith_data import search_hadith

            results = []
            for book_key in HADITH_BOOKS:
                try:
                    res = await search_hadith(keyword, book_key)
                    results.extend((book_key, r) for r in res)
                    if len(results) >= 10:
                        break
                except Exception:
                    continue

            if not results:
                await answer.reply_text(f"❌ لا توجد نتائج لـ «{keyword}»")
                return

            lines = [f"🔍 **نتائج البحث عن:** {keyword}\n"]
            for book_key, hadith in results[:10]:
                text = hadith.get("arab", hadith.get("text", ""))[:80]
                num = hadith.get("number", "")
                book_name = HADITH_BOOKS.get(book_key, {}).get("name", book_key)
                lines.append(f"📚 **{book_name}** - حديث {num}:\n  {text}...\n")
                lines.append(f"  → /hadith {book_key} {num}\n")

            await answer.reply_text("\n".join(lines))

        elif action == "_":
            await cq.answer()

    @app.on_message(filters.private & filters.command("hadith"))
    @safe_handler()
    async def hadith_inline(client, message):
        parts = message.text.split()
        if len(parts) == 3:
            book = parts[1].lower()
            try:
                number = int(parts[2])
            except ValueError:
                await message.reply_text(
                    "❌ استخدم: `/hadith [كتاب] [رقم]`\nمثال: `/hadith bukhari 1`"
                )
                return

            hadith = await get_hadith(book, number)
            if hadith:
                await message.reply_text(format_hadith(hadith))
            else:
                await message.reply_text("❌ لم يتم العثور على الحديث")

        elif len(parts) == 2:
            book = parts[1].lower()
            if book in HADITH_BOOKS:
                info = HADITH_BOOKS[book]
                await message.reply_text(
                    f"📚 **{info['name']}**\n───\n"
                    f"• العدد الإجمالي: {info['total']:,}\n"
                    f"• لعرض حديث: `/hadith {book} [رقم]`\n"
                    f"مثال: `/hadith {book} 1`"
                )
            else:
                books = "، ".join(HADITH_BOOKS.keys())
                await message.reply_text(f"❌ كتاب غير معروف. الكتب المتاحة: {books}")
