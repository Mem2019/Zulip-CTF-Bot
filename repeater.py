# 人类的本质是复读机，所以此repeater.py乃是最强人工智能
class Repeater:
	def __init__(self, send_message, threshold):
		self.records = {}
		self.send_message = send_message
		assert threshold > 1
		self.threshold = threshold
	def update(self, stream, subject, content):
		r = self.records.get((stream, subject))
		if r and r[0] == content:
			self.records[(stream, subject)] = (content, r[1] + 1)
			if r[1] + 1 == self.threshold:
				self.send_message(stream, subject, content)
		else:
			self.records[(stream, subject)] = (content, 1)
