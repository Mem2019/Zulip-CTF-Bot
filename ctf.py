import zulip
import re
from datetime import datetime
from repeater import Repeater
from enum import Enum
from ctf_type import *
from notion_sync import *

client = zulip.Client(config_file="./zuliprc")
with open("token_v2", "r") as f:
	token_v2 = str(f.read()).strip()

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
	return (stream, chall)

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
		return (stream, subject)

def solved(stream, subject, msg, args):
	chall = get_chall(stream, subject)
	if chall is None:
		send_message(stream, subject, "Error: not a challenge!")
	else:
		chall.solved = ChallState.Solved
		ret = "Great Work! Thanks to "
		for solver in chall.workings:
			ret += "@**%s** " % solver
		send_message(stream, subject, ret)
		return (stream, subject)

def status(stream, subject, msg, args):
	ret = ""
	ctf = get_ctf(stream)
	for cate in ctf.challenges:
		category = ctf.challenges[cate]
		ret += "*** ------------- %s ------------- ***\n" % cate
		for chall in category:
			ret += "%s: %s" % (chall, ', '.join(category[chall].workings))
			if category[chall].solved == ChallState.Solved:
				ret += " (solved!)"
			elif category[chall].solved == ChallState.Stuck:
				ret += " (stuck)"
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

def addNotion(stream, subject, msg, args):
	ctf = get_ctf(stream)
	if len(args) == 0:
		send_message(stream, subject, "Error: format is !gd [Google Doc Link]")
		return
	try:
		ctf.notion = NotionCTF(token_v2 ,args[0])
	except Exception as e:
		send_message(stream, subject, "Error, failed to create notion")
		raise e

def new_topic(stream, subject, msg, args):
	ctf = get_ctf(stream)
	for category_name, challs in ctf.challenges.items():
		for chall in challs.keys():
			send_message(stream, category_name + '-' + chall, "Topic for %s" % chall)

def helper(stream, subject, msg, args):
	send_message(stream, subject, """
ac/addchallenge/addchall [category] [name]: add a new challenge
w/work/working: mark yourself as working on the challenge of current topic
solve/solved: mark the challenge of current topic as solved
s/status: inspect status of current CTF
ls/links: summarize all links sent in current topic
fs/files: summarize all files uploaded in current topic
h/helper: show this helper message
notion [link]: add notion link
nt/newtopic: create topic for challenges that have no topic yet
""")

cmd_processor = dict(
	ac=add_chall, addchallenge=add_chall, addchall=add_chall,
	w=working, work=working, working=working,
	solve=solved, solved=solved,
	s=status, status=status,
	ls=get_links, links=get_links,
	fs=get_files, files=get_files,
	notion=addNotion,
	h=helper, help=helper,
	nt=new_topic, newtopic=new_topic)

def proc_cmd(stream, subject, msg, cmd):
	if len(cmd) == 0:
		return
	f = cmd_processor.get(cmd[0].lower())
	if f:
		return f(stream, subject, msg, cmd[1:])

reaction = {"丁佬强不强":"丁佬太强了"}

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

repeater = Repeater(send_message, 3)
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
	if content[0] == '!':
		return proc_cmd(stream, subject, msg, content[1:].split())
	else:
		proc_normal_msg(stream, subject, content, msg)
		repeater.update(stream, subject, content)

def create_event_queue():
	while True:
		event_queue = client.register(
			event_types=['message'])
		if event_queue['result'] == 'success':
			break
		sleep(1)
	return (event_queue, event_queue['last_event_id'])

event_queue, last_event_id = create_event_queue()
while True:
	print (event_queue)
	events = client.get_events(queue_id=event_queue['queue_id'],
		last_event_id=last_event_id, dont_block=True)
	if events['result'] != 'success':
		print ("Error: %s, reinitializing..." % str(events))
		event_queue, last_event_id = create_event_queue()
		continue
	modified = dict()
	for e in events['events']:
		if e['type'] != 'message':
			print ("Unknown type: %s" % e['type'])
		last_event_id = e['id']
		ret = msg_handler(e['message'])
		if ret:
			if modified.get(ret[0]):
				modified[ret[0]].append(ret[1])
			else:
				modified[ret[0]] = [ret[1]]
	try:
		for ctf,challs in modified.items():
			notion = get_ctf(ctf).notion
			if notion:
				notion.update_to_notion(get_ctf(ctf), challs)
		for ctf in ctfs.values():
			if ctf.notion:
				ctf.notion.update_from_notion(ctf, modified.get(ctf))
	except Exception as e:
		pass
	print (events)
