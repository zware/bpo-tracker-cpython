import re
import json
import random
from roundup.cgi.actions import Action
from roundup.cgi.exceptions import Redirect


def is_history_ok(request):
    user = request.client.userid
    db = request.client.db
    classname = request.classname
    nodeid = request.nodeid
    # restrict display of user history to user itself only
    if classname == 'user':
        return user == nodeid or 'Coordinator' in db.user.get(user, 'roles')
    # currently not used
    return True

def is_coordinator(request):
    user = request.client.userid
    db = request.client.db
    return 'Coordinator' in db.user.get(user, 'roles')

def is_triager(request, userid):
    db = request.client.db
    return 'Developer' in db.user.get(userid, 'roles')

def clean_ok_message(ok_message):
    """Remove nosy_count and message_count from the ok_message."""
    pattern = '\s*(?:nosy|message)_count,|,\s*(?:nosy|message)_count(?= edited)'
    return ''.join(re.sub(pattern, '', line) for line in ok_message) + '<br>'


def issueid_and_action_from_class(cls):
    """
    Return the id of the issue where the msg/file is/was linked
    and if the last "linking action" was 'link' or 'unlink'.
    """
    last_action = ''
    for entry in cls._klass.history(cls._nodeid):
        if 'unlink' in entry:
            last_unlink = entry
            last_action = 'unlink'
        elif 'link' in entry:
            last_entry = entry
            last_action = 'link'
    if last_action in ('link', 'unlink'):
        # the msg has been unlinked and not linked back
        # the link looks like: ('16', <Date 2011-07-22.05:14:12.342>, '4',
        #                       'link', ('issue', '1', 'messages'))
        return last_entry[4][1], last_action
    return None, None


def clas_as_json(request, cls):
    """
    Generate a JSON object that has the GitHub usernames as keys and as values
    true if the user signed the CLA, false if not, or none if there is no user
    associated with the GitHub username.
    """
    # pass the names as user?@template=clacheck&github_names=name1,name2
    names = request.form['github_names'].value.split(',')

    # Using cls.filter(None, {'github': names}) doesn't seem to work
    # so loop through the names and look them up individually
    result = {}
    for name in names:
        matches = cls.filter(None, {'github': name})
        if matches:
            # if more users have the same GitHub username, check that
            # at least one of them has signed the CLA
            value = any(match.contrib_form for match in matches)
        else:
            value = None
        result[name] = value

    return json.dumps(result, separators=(',',':'))


class RandomIssueAction(Action):
    def handle(self):
        """Redirect to a random open issue."""
        issue = self.context['context']
        # use issue._klass to get a list of ids, and not a list of instances
        issue_ids = issue._klass.filter(None, {'status': '1'})
        if not issue_ids:
            raise Redirect(self.db.config.TRACKER_WEB)
        # we create our own Random instance so we don't have share the state
        # of the default Random instance. see issue 644 for details.
        rand = random.Random()
        url = self.db.config.TRACKER_WEB + 'issue' + rand.choice(issue_ids)
        raise Redirect(url)


def init(instance):
    instance.registerUtil('is_history_ok', is_history_ok)
    instance.registerUtil('is_coordinator', is_coordinator)
    instance.registerUtil('is_triager', is_triager)
    instance.registerUtil('clean_ok_message', clean_ok_message)
    instance.registerUtil('issueid_and_action_from_class',
                          issueid_and_action_from_class)
    instance.registerUtil('clas_as_json', clas_as_json)
    instance.registerAction('random', RandomIssueAction)
