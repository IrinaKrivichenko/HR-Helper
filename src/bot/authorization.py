import asyncio
import threading


class UserAuthorizationManager:
    passwords = {
        "жаваранак", "верабей", "бусел", "варона", "цецярук", "сыч", 
        "галуб", "голуб", "качка", "дрозд", "сініца", "шпак", "салаўей",
        "зяблік", "сокал", "арол", "журавель", "чапля", "грак", "ластаўка",
        "свіргуль", "сава", "курганнік", "глушэц", "папугай", "лебедзь",
        "галаўка", "фазан", "канарэйка", "чомга", "бекас", "ківі", "вухань",
        "пугач", "зялёнагрудка", "курыца", "каваль", "гусь", "страўс",
        "іньдзюк", "казарка", "мандарынка", "крыжанка", "шыраканоска",
        "шылахвостка", "чырок", "нырэц", "нырок", "чарнец", "гага", "турпан",
        "сіньга", "маранка", "гогаль", "луток", "савук", "крахаль",
        "курапатка", "перапёлка", "рабчык", "пардва", "гагара", "гагач",
        "паганка", "коўра", "фламінга", "олуша", "пелікан", "баклан",
        "бугай", "кваква", "каравайка", "колпіца", "скапа", "асаед", "каршун", "арлан", "сіп", "грыф", "лунь",
        "ястраб", "шуляк", "канюк", "беркут", "пустальга", "шулёнак",
        "кобчык", "дзербнік", "дрымлюк", "кабец", "балабан", "сапсан",
        "падарожнік", "даўгахвост", "драч", "пастушок", "пагоныч",
        "пагоніч", "чаротніца", "лысуха", "дроп", "стрэпет", "сявец",
        "сеўка", "гальштучнік", "зуёк", "хрустан", "крывок", "хадулачнік",
        "шыладзюб", "марадунка", "перавозчык", "чарняк", "шчогаль",
        "селянец", "паручайнік", "цякун", "случок", "кулон", "вераценнік",
        "грыцук", "каменешарка", "пясочнік", "пясчанка", "верабей",
        "белахвосты", "марскі", "кіркун", "чорнаваллёвік", "чырвонаваллёвік",
        "гразевік", "баталён", "гаршнэп", "стучок", "дубальт", "слонка",
        "плывунчык", "ціркушка", "чайка", "танкадзюбая", "чорнагаловая",
        "клыгун", "шызая", "рагатуха", "клуша", "рагатун", "марская",
        "рыбачка", "крачка", "крычка", "чэграва", "палярная", "паморнік",
        "саджа", "клінтух", "вяхір", "туркаўка", "зязюля", "сіпуха", "сплюшка", "бярозаўка",
        "сіпель", "кугакаўка", "ляляк", "зімародак", "шчурка", "сіваграк", "удод", "круцігалоўка",
        "дзяцел", "жаўна", "грычун", "саракуш", "авяльга", "кукша", "сойка", "сарока",
        "арэхаўка", "каўка", "вусатая сініца", "жаўрук", "свіргуль", "землянка", "лястоўка",
        "маскоўка", "чубатая сініца", "блакітніца", "рэмез", "апалоўнік", "глінянка",
        "паўзунок", "крапіўнік", "валавока", "аляпка", "каралёк", "пячураўка", "перасмешка",
        "чаротаўка", "чарацянка", "мармытуля", "цвыркун", "леска", "валасеніца", "малінаўка",
        "салавей", "кралька", "рудахвостка", "падкаменка", "ерчык", "сіняхвостка", "рабіннік",
        "дзяраба", "завірушка", "пліска", "сітаўка", "свірстун", "амялушка", "стрынакта",
        "дуброўнік", "сняжурка", "пуначка", "берасцянка", "зябок", "юрок", "шчурок", "чаромашнік", "зелянушка",
        "крыжадзюб", "яловік", "чачотка", "чыж", "шчыгел", "канаплянка", "гіль", "таўстадзюб", "верабей"
    }
    
    def __init__(self):
        self.authorized_users = {}
        self.lock = threading.Lock()
        self.application = None

    def set_application(self, application):
        self.application = application

    async def send_logout_message(self, user, chat_id):
        message = f"You @{user} have been logged out🙃\nBye bye! See you soon!"
        await self.application.send_message(chat_id=chat_id, text=message)

    async def add_user(self, user, password, update):
        if password.lower() in self.passwords:
            with self.lock:
                self.authorized_users[user] = update.effective_chat.id
                print("chat_id = ", self.authorized_users[user])
                await update.message.reply_text("Hey! Glad you're here!")
            return True
        return False

    async def remove_user(self, user, word, update):
        if word.lower().strip() == "logout":
            with self.lock:
                if user in self.authorized_users:
                    chat_id = self.authorized_users.pop(user)
                    # await self.send_logout_message(user, chat_id)
                    await update.message.reply_text("Bye bye! See you soon!")
            return True
        return False

    def is_user_authorized(self, user):
        with self.lock:
            return user in self.authorized_users

    def reset_authorized_users(self):
        with self.lock:
            users_to_notify = self.authorized_users.copy()
            for user in users_to_notify:
                if user != 'irina_199':
                    chat_id = self.authorized_users.pop(user)
                    # asyncio.run_coroutine_threadsafe(
                    #     self.send_logout_message(user, chat_id),
                    #     asyncio.get_event_loop()
                    # )


auth_manager = UserAuthorizationManager()
