import json
import logging

from vkbottle import (
    BaseStateGroup,
    Keyboard,
    KeyboardButtonColor,
    OpenLink,
    Text,
)
from vkbottle.bot import Bot, Message

import config

# logging
logging.getLogger("vkbottle").setLevel(logging.INFO)


# state machine for getting answer
class SuperStates(BaseStateGroup):
    ANSWER_STATE = "answer"


class VK_BOT:
    def __init__(self, token):
        self.bot = Bot(token=token)
        with open("tests.json", "r") as f:
            self.data = json.load(f)

    def start(self):
        @self.bot.on.message(text=["Начать", "/start"], state=None)
        async def hello(message: Message):
            await message.answer(
                f"Привет, {(await self.bot.api.users.get(user_ids=message.from_id))[0].first_name}!\nДобро пожаловать в цифровую экспедицию «Тропа памяти».\nЯ — твой гид по истории Металлургического района.",
                keyboard=Keyboard(inline=False, one_time=False).add(
                    Text("Меню"), color=KeyboardButtonColor.SECONDARY
                ),
            )
            await get_rules(message)

        @self.bot.on.message(text=["Меню", "/menu"])
        async def get_menu(message: Message):
            state_peer = await self.bot.state_dispenser.get(message.peer_id)
            if state_peer is not None:
                await message.answer(
                    f"❗Вы вышли из теста: {state_peer.payload.get('test')}"
                )
                await self.bot.state_dispenser.delete(message.peer_id)
            else:
                await message.answer(
                    "Меню",
                    keyboard=Keyboard(inline=True)
                    .add(Text("Тесты"), color=KeyboardButtonColor.POSITIVE)
                    .row()
                    .add(Text("Правила"), color=KeyboardButtonColor.SECONDARY)
                    .row()
                    .add(Text("Контакты"), color=KeyboardButtonColor.PRIMARY),
                )

        @self.bot.on.message(text=["Правила", "/rules"], state=None)
        async def get_rules(message: Message):
            await message.answer(
                "📜 Правила:\n— 5 вопросов разной сложности,\n"
                "— Я задаю вопрос и даю 3 варианта ответа.\n"
                "— В конце ты узнаешь свой результат.\n"
                "Для перехода к тестам нажми кнопку Меню\n"
                "Удачи! 🍀"
            )

        @self.bot.on.message(text=["Контакты", "/contacts"], state=None)
        async def get_contacts(message: Message):
            await message.answer(
                "Добро пожаловать в раздел контактов! 📲\n\n"
                "Ниже — способы связаться с организаторами проекта. Выбирайте удобный канал и пишите — будем рады помочь.",
                keyboard=Keyboard(inline=True)
                .add(OpenLink(label="ВК", link="https://vk.com/lerron_len"))
                .row()
                .add(Text("Почта"))
                .row()
                .add(
                    OpenLink(
                        label="Мах",
                        link="https://max.ru/u/f9LHodD0cOJ_XVJ0RggZRkMOiiupBik1VhppTfufR7jmBnBPvS8KAHqdAZ0",
                    )
                ),
            )

        @self.bot.on.message(text=["Почта", "/email"], state=None)
        async def get_email(message: Message):
            await message.answer("ignatova.v04@mail.ru")

        @self.bot.on.message(text=["Тесты", "/tests"], state=None)
        async def get_tests(message: Message):
            keyboard = Keyboard(inline=True)
            for i in self.data:
                keyboard.add(Text(i), color=KeyboardButtonColor.POSITIVE)
                keyboard.row()
            await message.answer("Все доступные тесты: ", keyboard=keyboard)

        async def send_question(message: Message):
            state_peer = await self.bot.state_dispenser.get(message.peer_id)
            keyboard = Keyboard(inline=True)
            for i in self.data[state_peer.payload.get("test")][0]["questions"][
                state_peer.payload.get("current_question")
            ]["options"]:
                keyboard.add(Text(i))
                keyboard.row()
            if (
                self.data[state_peer.payload.get("test")][0]["questions"][
                    state_peer.payload.get("current_question")
                ]["type"]
                == "text"
            ):
                await message.answer(
                    self.data[state_peer.payload.get("test")][0]["questions"][
                        state_peer.payload.get("current_question")
                    ]["text"],
                    keyboard=keyboard,
                )

        @self.bot.on.message(state=SuperStates.ANSWER_STATE)
        async def check_answer(message: Message):
            state_peer = message.state_peer
            if (
                message.text
                in self.data[state_peer.payload["test"]][0]["questions"][
                    state_peer.payload["current_question"]
                ]["options"]
            ):
                if (
                    self.data[state_peer.payload["test"]][0]["questions"][
                        state_peer.payload["current_question"]
                    ]["correct_answer"]
                    == message.text
                ):
                    state_peer.payload["correct_answers"] += 1
                    await message.answer(
                        self.data[state_peer.payload["test"]][0]["questions"][
                            state_peer.payload["current_question"]
                        ]["comment"]
                    )
                else:
                    await message.answer(
                        "Почти угадали! 😅 На самом деле это "
                        f"{self.data[state_peer.payload['test']][0]['questions'][state_peer.payload['current_question']]['correct_answer']}. "
                        "Не расстраивайтесь, следующий вопрос будет интереснее!"
                    )
                if (
                    len(self.data[state_peer.payload["test"]][0]["questions"]) - 1
                    == state_peer.payload["current_question"]
                ):
                    await finish_test(message)
                else:
                    state_peer.payload["current_question"] += 1
                    await self.bot.state_dispenser.set(
                        message.peer_id, state_peer.state, **state_peer.payload
                    )
                    await send_question(message)
            else:
                await message.answer(
                    "Такого ответа нет, попробуйте еще раз.\nЧтобы выйти нажмите кнопку Меню или отправьте команду /menu"
                )
                await send_question(message)

        @self.bot.on.message(state=None)
        async def start_test(message: Message):
            if message.text in self.data:
                await self.bot.state_dispenser.set(
                    message.peer_id,
                    SuperStates.ANSWER_STATE,
                    test=message.text,
                    current_question=0,
                    correct_answers=0,
                )
                await message.answer(self.data[message.text][0]["start_message"])
                await message.answer("Для выхода из теста нажмите кнопку Меню")
                await send_question(message)
            else:
                await message.answer("Команда не найдена")

        async def finish_test(message: Message):
            state_peer = await self.bot.state_dispenser.get(message.peer_id)
            await message.answer(
                f"\nВаш результат: {state_peer.payload.get('correct_answers')}"
                f" из {state_peer.payload.get('current_question') + 1}"
            )
            await message.answer(
                self.data[state_peer.payload.get("test")][0]["finish_message"]
            )
            await self.bot.state_dispenser.delete(message.peer_id)

        self.bot.run_forever()


if __name__ == "__main__":
    VK_BOT(config.TOKEN).start()
