import zulip
import re
from datetime import datetime
client = zulip.Client(config_file="./zuliprc")
# result = client.list_subscriptions()
# result = client.get_streams()
# result = client.add_subscriptions(streams=[{'name': "SomeCTF"}])
# print (result)

class Challenge:
	def __init__(self):
		self.solved = False
		self.workings = set()
		self.links = []
		self.files = []

class CTF:
	def __init__(self):
		self.challenges = {} # category->Challenge
		self.googleDocLink = None
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

ctfs = {}

def get_ctf(name):
	global ctfs
	tmp = ctfs.get(name)
	if tmp is None:
		tmp = CTF()
		ctfs[name] = tmp
	return tmp

def get_chall(ctf, chall):
	ctf = get_ctf(ctf)
	separator = chall.find('-')
	if separator >= 0:
		return ctf.get_chall(chall[:separator], chall[separator+1:])

def send_message(stream, subject, msg):
	msg_ = dict(type = 'stream',
			to = stream,
			topic = subject,
			content = msg)
	client.send_message(msg_)

def add_chall(stream, subject, msg, args):
	def get_args():
		if len(args) < 2:
			if len(args) == 1:
				split_idx = args[0].find('-')
				if split_idx >= 0:
					return (args[0][:split_idx], args[0][split_idx+1:])
		else:
			return args
	args = get_args()
	if args is None:
		send_message(stream, subject, "Error: format is !ac [category] [challenge]")
		return

	if args[0].find('-') >= 0:
		send_message(stream, subject, "Error: category cannot contain '-'")
		return

	chall = "%s-%s" % (args[0], args[1]) # get topic name
	send_message(stream, chall, "New Challenge: %s" % chall) # say sth in topic
	get_ctf(stream).get_chall(args[0], args[1]) # create the challenge storage

def parse_users(users):
	ret = []
	while True:
		if len(users) == 0:
			return ret
		r = re.search("@\\*\\*([^@\\*]*)\\*\\*", users)
		if r is None:
			ret.append(users)
			return ret
		if r.start() != 0:
			ret.append(users[:r.start()])
		if len(r.group(1)) > 0:
			ret.append(r.group(1))
		users = users[r.end():]
def working(stream, subject, msg, args):
	chall = get_chall(stream, subject)
	if chall is None:
		send_message(stream, subject, "Error: not a challenge!")
	else:
		if len(args) == 0:
			chall.workings.add(msg['sender_full_name'])
		else:
			for arg in args:
				for user in parse_users(arg):
					chall.workings.add(user)

def solved(stream, subject, msg, args):
	chall = get_chall(stream, subject)
	if chall is None:
		send_message(stream, subject, "Error: not a challenge!")
	else:
		chall.solved = True
		ret = "Great Work! Thanks to "
		for solver in chall.workings:
			ret += "@**%s** " % solver
		send_message(stream, subject, ret)

def status(stream, subject, msg, args):
	ret = ""
	ctf = get_ctf(stream)
	for cate in ctf.challenges:
		category = ctf.challenges[cate]
		ret += "*** ------------- %s ------------- ***\n" % cate
		for chall in category:
			ret += "%s: %s" % (chall, ', '.join(category[chall].workings))
			if category[chall].solved:
				ret += " (solved!)"
			ret += '\n'
	send_message(stream, subject, ret)

def get_msg(stream, subject, msg, args, get_callback, header):
	chall = get_chall(stream, subject)
	if chall is None:
		send_message(stream, subject, "Error: not a challenge!")
	else:
		ret = "***** %s *****\n" % header
		for elem in get_callback(chall):
			ret += "** Sent by %s at %s **\n" % \
				(elem[0], datetime.fromtimestamp(elem[1]))
			ret += "```quote\n"
			ret += elem[2]
			ret += "\n```\n"
		send_message(stream, subject, ret)

get_links = lambda a,b,c,d : get_msg(a,b,c,d,lambda c : c.links, "All links sent in this topic")
get_files = lambda a,b,c,d : get_msg(a,b,c,d,lambda c : c.files, "All files uploaded in this topic")

def addGoogleDocLink(stream, subject, msg, args):
	ctf = get_ctf(stream)
	if len(args) == 0:
		send_message(stream, subject, "Error: format is !gd [Google Doc Link]")
		return
	ctf.googleDocLink = args[0]

cmd_processor = dict(
	ac=add_chall, addchallenge=add_chall, addchall=add_chall,
	w=working, work=working, working=working,
	solve=solved, solved=solved,
	s=status, status=status,
	ls=get_links, links=get_links,
	fs=get_files, files=get_files,
	gd=addGoogleDocLink, googledoc=addGoogleDocLink)

def proc_cmd(stream, subject, msg, cmd):
	f = cmd_processor.get(cmd[0].lower())
	if f:
		f(stream, subject, msg, cmd[1:])

reaction = {"丁佬强不强":"丁佬太强了", "成功":"失败"}

file_regex = "\\[.*\\]\\(((https:\\/\\/)?[a-zA-Z0-9_].zulipchat.com)?/user_uploads.*\\)"
link_regex = "(https?:\\/\\/)?(www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b([-a-zA-Z0-9()@:%_\\+.~#?&//=]*)"
def proc_normal_msg(stream, subject, content, msg):
	react = reaction.get(content)
	if not (react is None):
		send_message(stream, subject, react)
		return
	chall = get_chall(stream, subject)
	if chall:
		if re.search(file_regex, content):
			chall.files.append(( \
				msg['sender_full_name'], msg['timestamp'], content))
		elif re.search(link_regex, content):
			chall.links.append(( \
				msg['sender_full_name'], msg['timestamp'], content))

def msg_handler(msg):
	if msg['type'] != 'stream' or msg['sender_full_name'] == "CTF":
		return # ignore private msg and msg sent by itself
	stream = msg['display_recipient']
	subject = msg['subject']
	content = msg['content']
	if content.find("@**CTF**") >= 0:
		res = client.add_subscriptions(streams=[{'name': stream}])
		if res['result'] != 'success':
			send_message(stream, subject, str(res))
		# add subscription if bot is mentioned
	elif content[0] == '!':
		proc_cmd(stream, subject, msg, content[1:].split())
	else:
		proc_normal_msg(stream, subject, content, msg)



event_queue = client.register(
	event_types=['message']
)
last_event_id = -1
while True:
	events = client.get_events(queue_id=event_queue['queue_id'],
		last_event_id=last_event_id, dont_block=True)
	if events['result'] != 'success':
		print ("Error: %s, reinitializing..." % str(events))
		event_queue = client.register(
			event_types=['message'])
		last_event_id = -1
		continue
	for e in events['events']:
		if e['type'] != 'message':
			print ("Unknown type: %s" % e['type'])
		last_event_id = e['id']
		msg_handler(e['message'])
	print (events)
