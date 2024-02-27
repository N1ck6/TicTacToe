import discord
from discord.ext import commands
from typing import List
from asyncio import sleep

TOKEN = "TOKEN"
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='/', intents=intents)


class Button(discord.ui.Button['TicTacToe']):
    def __init__(self, x: int, y: int, value: int):
        if value == 0:
            label = '\u200b'
            style = discord.ButtonStyle.secondary
            disabled = False
        else:
            if value == -1:
                label = '╳'
                style = discord.ButtonStyle.danger
                disabled = True
            else:
                label = 'Ｏ'
                style = discord.ButtonStyle.success
                disabled = True
        super().__init__(style=style, label=label, row=y, custom_id=str(x), disabled=disabled)
        self.x = x


    async def callback(self, interaction: discord.Interaction):  # Called on button press
        assert self.view is not None
        view: TicTacToe = self.view
        if view.auto and interaction.user.id != view.id and interaction.user.id != view.id1:
            await interaction.response.send_message("This is not your game! Don't ruin fun", ephemeral=True)
            return
        if view.busy:
            view.busy = False
            await interaction.response.send_message("Not your turn! Don't ruin fun", ephemeral=True)
            return
        if not view.auto and interaction.user.id != view.id and view.id1 == -1:
            view.id1 = interaction.user.id
            view.other = interaction.user
            if view.current_player == -1:
                view.id, view.id1 = view.id1, view.id
                view.main, view.other = view.other, view.main
        state = view.board[self.x]
        if state in (-1, 1):
            return
        view.busy = True
        id = interaction.message.id
        if view.current_player == -1:
            if not view.auto and interaction.user.id != view.id:
                await interaction.response.send_message("Not your turn! Don't ruin fun", ephemeral=True)
                view.busy = False
                return
            self.style = discord.ButtonStyle.danger
            self.label = '╳'
            self.disabled = True
            view.board[self.x] = -1
            if not view.auto and view.id1 == -1:
                content = f"Waiting for ttt partner... Place ⭕"
            else:
                content = f"{view.other}'s turn. Place ⭕"
            if not view.auto:
                view.current_player = 1
        else:
            if not view.auto and interaction.user.id != view.id1:
                await interaction.response.send_message("Not your turn! Don't ruin fun", ephemeral=True)
                view.busy = False
                return
            self.style = discord.ButtonStyle.success
            self.label = 'Ｏ'
            self.disabled = True
            view.board[self.x] = 1
            content = f"{view.main}'s turn. Place ❌"
            if not view.auto:
                view.current_player = -1
        result = view.check_board_winner()
        if result is not None:
            content = result
            for child in view.children:
                child.disabled = True
            view.stop()
        await interaction.response.edit_message(content=content, view=view)

        if view.auto and result is None:  # Bot's turn
            await sleep(0.7)  # Bot response speed
            move = view.predict(view.player)  # Choose Bot's move
            button = [x for x in view.children if x.custom_id == str(move)][0]
            button.disabled = True
            view.board[move] = view.player
            if view.player == -1:
                button.label = '╳'
                content = f"{view.other}'s turn. Place ⭕"
                button.style = discord.ButtonStyle.danger
            else:
                button.label = 'Ｏ'
                content = f"{view.main}'s turn. Place ❌"
                button.style = discord.ButtonStyle.success
            result = view.check_board_winner()
            if result is not None:
                content = result
                for child in view.children:
                    child.disabled = True
                view.stop()
            await interaction.followup.edit_message(content=content, view=view, message_id=id)
        view.busy = False


class TicTacToe(discord.ui.View):
    children: List[Button]

    def __init__(self, mode, author):
        super().__init__()
        self.id = author.id
        self.id1 = -1
        self.player = -5
        self.main = author
        self.other = 'Bot'
        if mode == "player":
            self.auto = False
        else:
            if mode.lower() == 'x':
                self.player = 1
            elif mode.lower() == 'o':
                self.id, self.id1 = self.id1, self.id
                self.main, self.other = self.other, self.main
                self.player = -1
            self.auto = True
        self.busy = False
        self.current_player = -1
        self.board = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        if self.player == -1:  # Bot's first move
            self.board[4] = -1
            self.current_player = 1
        self.pairs = [[0, 1, 2],  # row
                      [3, 4, 5],
                      [6, 7, 8],
                      [0, 3, 6],  # col
                      [1, 4, 7],
                      [2, 5, 8],
                      [0, 4, 8],  # dial
                      [2, 4, 6]]
        self.edges = [0, 2, 6, 8]
        for x in range(9):
            self.add_item(Button(x, x // 3, self.board[x]))


    def check_board_winner(self):
        for pair in self.pairs:
            s = sum([self.board[i] for i in pair])
            if s == 3:
                return f'{self.other} Won! / {self.main} Lost!'
            elif s == -3:
                return f'{self.main} Won! / {self.other} Lost!'
        if all(i != 0 for i in self.board):
            return f"{self.main} / {self.other} - Tie!"
        return None


    def mx(self, x):
        count = 0
        for i in range(9):
            if (i % 3 == x % 3 and i in [x + 3, x - 3]) or (i // 3 == x // 3 and i in [x + 1, x - 1]) or \
                    (i // 3 in [x // 3 - 1, x // 3 + 1] and i in [x - 4, x - 2, x + 2, x + 4]):
                if self.board[i] == -self.player:
                    count += 1
        return count

    def dual_fork(self):
        goal = -1
        for i in range(9):
            count = 0
            temp_board = self.board.copy()
            if temp_board[i] != 0:
                continue
            temp_board[i] = self.player
            for pair in self.pairs:
                s = [self.board[i] for i in pair]
                if s.count(0) == 1 and s.count(self.player) == 2:
                    count += 1
            if count >= 2:
                goal = i
        if goal == -1:
            for i in range(9):
                count = 0
                temp_board = self.board.copy()
                if temp_board[i] != 0:
                    continue
                temp_board[i] = -self.player
                for pair in self.pairs:
                    s = [self.board[i] for i in pair]
                    if s.count(0) == 1 and s.count(-self.player) == 2:
                        count += 1
                if count >= 2 and i in self.edges:
                    goal = i
        if goal == -1:
            s = [self.board[i] for i in self.edges]
            if self.board[4] == -self.player and s.count(-self.player) == s.count(-self.player) == 1:
                goal = self.edges[s.index(0)]
        return goal


    def predict(self, player):  # Don't let this sequence of if statements beat you lol
        for pair in self.pairs:
            s = [self.board[i] for i in pair]
            if s.count(0) == 1 and s.count(self.player) == 2:
                return pair[s.index(0)]
        for pair in self.pairs:
            s = [self.board[i] for i in pair]
            if s.count(0) == 1 and s.count(-self.player) == 2:
                return pair[s.index(0)]
        forking = self.dual_fork()
        if forking != -1:
            return forking
        if self.board[4] == 0:
            return 4
        for i in self.pairs[6:]:
            if self.board[i[0]] == -player and self.board[i[-1]] == 0:
                return i[-1]
            elif self.board[i[-1]] == -player and self.board[i[0]] == 0:
                return i[0]
        empty = [i for i in range(9) if self.board[i] == 0]
        if len(empty):
            empty.sort(key=lambda x: self.mx(x), reverse=True)
            return empty[0]


@client.command()
async def ttt(ctx: commands.Context, *args):  # chat command to start
    await ctx.message.delete(delay=10)
    if not args or args[0].lower() not in ['x', 'o', 'player']:
        await ctx.send(f'Hi, {ctx.author}! Down to a game of Tic Tac Toe? Commands:', delete_after=10)
        await ctx.send('/ttt x | /ttt o - Play against me as ❌ | ⭕', delete_after=10)
        await ctx.send('/ttt player - 2 players mode', delete_after=10)
    else:
        if args[0].lower() != "player":
            if args[0].lower() == 'o':
                message = "Bot's turn. Place ❌"
            else:
                message = f"{ctx.author}'s turn. Place ❌"
        else:
            message = "Waiting for ttt partner... Place ❌"
        await ctx.send(message, view=TicTacToe(args[0].lower(), ctx.author))


client.run(TOKEN, log_handler=None)  # delete log_handler to start logging errors
