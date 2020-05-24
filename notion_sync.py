from notion.client import NotionClient
from notion.block import TodoBlock
from notion.user import User
import json
import requests
from ctf_type import *

class NotionCTF:
	def _get_status(status):
		status = status.lower()
		if status.find("stuck") >= 0:
			return ChallState.Stuck
		elif status.find("solve") >= 0:
			return ChallState.Solved
		else:
			return ChallState.Progress
	STATUS_TOSTR = ['in progress 🤔', 'stuck 😣', 'solved 😎']
	def _set_status(status):
		return NotionCTF.STATUS_TOSTR[status]
	def _get_subscribers(client):
		r = requests.post("https://www.notion.so/api/v3/getSubscriptionData", \
			json=({'spaceId': client.current_space.id}), \
			cookies={'token_v2':token_v2})
		ret = dict()
		for user in r.json()['members']:
			ret[user.given_name] = User(client=client, id=x['userId'])
		return ret

	def __init__(self, token_v2, url):
		self.client = NotionClient(token_v2=token_v2)
		self.users = _get_subscribers(self.client)
		self.cv = self.client.get_collection_view(url)
		self._init_users()

	# update all challenges, except those in `updated`,
	# into Python
	def update_from_notion(self, ctf, updated):
		if updated is None:
			updated = []
		rows = self.cv.collection.get_rows()
		for row in rows:
			if row.Type.lower() + '-' + row.Name in updated:
				continue
			if row.Name is None or row.Type is None:
				continue
			chall = ctf.get_chall(row.Type.lower(), row.Name)
			chall.solved = _get_status(record.Status)
			chall.workings = map(lambda x : x.given_name, record.Candidates)

	def _get_user(self, name):
		r = self.users.get(name)
		if r:
			return r
		self.users = _get_subscribers(self.client)
		return self.users.get(name)

	def _update_row(self, row, challenge):
		row.Status = _get_status(challenge.solved)
		candidates = []
		for user in challenge.workings:
			r2 = self._get_user(user)
			if r2:
				candidates.append(r2)
		row.Candidates = candidates

	# update challenges in `to_update` to notion
	# if the challenge does not exist, create one first
	def update_to_notion(self, ctf, to_update):
		row_map = dict()
		rows = self.cv.collection.get_rows()
		visited = [False] * len(to_update)
		for row in rows: # iterate over current rows
			try:
				idx = to_update.index(row.Type.lower() + '-' + row.Name)
				challenge = ctf.get_chall(row.Type.lower(), row.Name)
				self._update_row(row, challenge)
				visited[idx] = True # update if in to_update
			except Exception as e: # not in to_update
				pass
		for i in range(0, len(visited)):
			if not visited[i]:
				idx = to_update[i].find('-')
				category, name = to_update[i][:idx], to_update[i][idx+1:]
				challenge = ctf.get_chall(category, name)
				row = cv.collection.add_row()
				row.Name = name
				row.Type = category
				self._update_row(row, challenge)