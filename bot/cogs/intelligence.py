import discord
from discord.ext import commands
import random

class Intelligence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="tips", aliases=["batting"], description="Learn HC Batting Fundamentals")
    async def tips_cmd(self, ctx):
        embed = discord.Embed(
            title="🧠 HC BATTING FUNDAMENTALS",
            description="HC is a mind game. Every decision you make should punish the bowler's expectation.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="1. Basic Tendencies",
            value="🏏 **Never** rotate the strike on your first ball.\n"
                  "⚠️ **Avoid** 1 / 3 / 4 immediately after playing 6.\n"
                  "🔁 **Avoid** repeatedly playing 4.\n"
                  "⚡ **Avoid** playing 6 immediately after 2.\n"
                  "*Note: These are general tendencies, not absolute laws! Opponents will adapt!*",
            inline=False
        )
        
        embed.add_field(
            name="2. Bowler Manipulation",
            value="Don't just predict what the bowler will do. **Make the bowler believe you are going to do something — then punish that expectation.**",
            inline=False
        )
        
        embed.add_field(
            name="3. First 2-3 Balls Strategy",
            value="Use the first few balls against a new bowler for information. Observe their tendencies. **Survive → Read → Manipulate → Attack.**",
            inline=False
        )
        
        embed.add_field(
            name="4. What the Bowler Thinks",
            value="• If they spam **4/5/6**: They think you'll play BIG.\n"
                  "• If they spam **0/1/2/3**: They think you'll play SMALL.\n"
                  "*Counter it: If they think BIG, occasionally play small to reinforce it, then attack with 5/6.*",
            inline=False
        )
        
        embed.set_footer(text="Use !training to practice scenarios!")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="coach", description="Get a personalized tip from your HC Coach")
    async def coach_cmd(self, ctx):
        # Since we don't have a deep ball-by-ball database yet, we will provide a random coaching challenge
        challenges = [
            "Break your first-ball pattern today. Play something you never usually open with.",
            "If the bowler spams a number more than once in the last 6 balls, do not blindly copy it.",
            "Watch your Strike Rate. If it's below 200, the bowler might start using 0/1/2 to restrict you.",
            "Survive the first 3 balls against a new bowler without attacking. Gather information.",
            "After hitting a 6, do NOT play a 1, 3, or 4 on the very next ball."
        ]
        
        embed = discord.Embed(
            title="🏏 YOUR HC COACH",
            color=discord.Color.green()
        )
        embed.add_field(name="🎯 Today's Challenge:", value=f"> {random.choice(challenges)}")
        embed.set_footer(text="HC is about psychology and pattern recognition. Adapt!")
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="training", description="Practice reading HC situations")
    async def training_cmd(self, ctx):
        scenarios = [
            {
                "text": "New bowler. Last 3 balls: `5 → 6 → 5`. He appears to expect you to play big. What do you do?",
                "options": ["A: 6", "B: 1", "C: 5", "D: 4"],
                "correct_index": 1,
                "explanation": "Playing a low number (like 1) reinforces their belief that they are restricting you, setting them up for a big hit later."
            },
            {
                "text": "You just hit a massive 6. The bowler is angry. What should you AVOID playing next?",
                "options": ["A: 6", "B: 2", "C: 5", "D: 1 / 3 / 4"],
                "correct_index": 3,
                "explanation": "Avoid 1, 3, or 4 immediately after playing 6, as bowlers often try to catch you rotating strike."
            },
            {
                "text": "The bowler's last 6 moves are: `5 • 5 • 2 • 5 • 5 • 1`. What is your strategy?",
                "options": ["A: Blindly copy 5", "B: Avoid 5, they are spamming it", "C: Play 6", "D: Play 0"],
                "correct_index": 1,
                "explanation": "They have spammed 5 four times. Blindly copying it is highly risky. Avoid it!"
            }
        ]
        
        scenario = random.choice(scenarios)
        
        embed = discord.Embed(title="🧠 SCENARIO", description=scenario["text"], color=discord.Color.purple())
        for opt in scenario["options"]:
            embed.description += f"\n{opt}"
            
        embed.set_footer(text="Think carefully... (This is an interactive concept, full training mode coming soon!)")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Intelligence(bot))
