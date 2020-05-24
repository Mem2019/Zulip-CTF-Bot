from enum import Enum

class ChallState(Enum):
	Progress = 0
	Stuck = 1
	Solved = 2

class Challenge:
	def __init__(self):
		self.solved = ChallState.Progress
		self.workings = set()
		self.links = []
		self.files = []

class CTF:
	def __init__(self):
		self.challenges = {} # category->Challenge
		self.notion = None
	def get_chall(self, category, name):
		category_ = self.challenges.get(category);
		if category_ is None:
			category_ = {}
			self.challenges[category] = category_
		chall = category_.get(name)
		if chall is None:
			chall = Challenge()
			category_[name] = chall
		return chall

def get_chall(ctf, chall):
	ctf = get_ctf(ctf)
	separator = chall.find('-')
	if separator >= 0:
		return ctf.get_chall(chall[:separator], chall[separator+1:])