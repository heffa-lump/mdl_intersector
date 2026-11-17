from bs4 import BeautifulSoup
import requests
import time

class Work:
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url

    def __repr__(self):
        return self.name + ':' + self.url
    
    def __hash__(self):
        return hash(self.url)
    
    def __eq__(self, __value: object) -> bool:
        return (type(self) == type(__value) and self.url == __value.url) or \
               (type(__value) == str and self.url == __value)


ROLE_VALUES = {'Main': 0,
               'Support': 1,
               'Guest': 2}
class Role:
    def __init__(self, work: Work, character_name: str, role_type: str):
        self.work = work
        self.character_name = character_name
        self.type = role_type
    
    def __eq__(self, __value: object) -> bool:
        return self.work.url == __value.work.url and\
               self.character_name == __value.character_name
    
    def __repr__(self) -> str:
        return "%s, %s (%s)" % (self.work.name, self.character_name, self.type)

    def __hash__(self) -> int:
        return hash(self.__repr__())


class Actor:
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url
        self.roles = []
        
    def __repr__(self):
        return self.name
    
    def addRole(self, work: Work, character_name: str, role_type: str):
        self.roles.append(Role(work, character_name, role_type))

    def addRolesFrom(self, other):
        self.roles += other.roles

def progressMessage(done, total, doing):
    return "Looking through %i/%i: %s" % (done, total, doing)


def getHtmlDummy(url: str):
    if url == 'https://mydramalist.com/dramalist/mxticktock/completed':
        return open('html_cache/mxticktock_completed.html').read()
    elif url == 'https://mydramalist.com/683119-shao-nian-ge-xing/cast':
        return open('html_cache/tboy_cast.html').read()
    else:
        return ''

def getHtml(url: str) -> tuple[str, str]:
    """
    Returns an (error message, content) tuple. Error message will
    be empty if there is no error.
    """
    time.sleep(0.1)
    try:
        r = requests.get(url)
        if r.status_code != requests.codes.ok:
            return 'Error returning page for %s' % url, ''
        return '', r.content
    except:
        return 'Error returning page for %s. Malformed URL?' % url, ''

def workUrlToActors(url) -> tuple[str, dict]:
    err, html = getHtml(url if url.endswith('cast') else url + '/cast')
    if err:
        return err, {}
    soup = BeautifulSoup(html, 'html.parser')

    # Get title
    work = Work('Title not found', url)
    title_tag = soup.find('h1', 'film-title')
    if title_tag:
        work = Work(title_tag.text, url)

    # Get actors
    actor_dict = {}
    def fillActorDict(role_type):
        tags = soup.find_all(lambda tag: tag.name == 'small' and \
                          hasattr(tag, 'text') and \
                          tag.text == role_type + ' Role')
        for tag in tags:
            div = tag.parent
            if not (div.a and 'href' in div.a.attrs):
                print('could not find url in actor', div)
                continue
            actor_url = div.a['href']
            if not div.a.b:
                print('could not find name for actor', div)
                continue
            name = div.a.b.text

            role_name = 'Unnamed'
            role_tag = div.parent.find(lambda tag: tag.name == 'small' and \
                                       'title' in tag.attrs)
            # Sometimes the role name is a hyperlink
            if not role_tag:
                role_tag = div.parent.find(lambda tag: tag.name == 'small' and \
                                           not len(tag.attrs) and
                                           tag.a)
            if role_tag:
                role_name = role_tag.text
            else:
                print('could not find role for actor', div.parent)

            actor = Actor(name, actor_url)
            actor.addRole(work, role_name, role_type)
            actor_dict[actor_url] = actor
            print(work.name, actor.name, '|', role_name, role_type)

    fillActorDict('Main')
    fillActorDict('Support')
    fillActorDict('Guest')
    return '', actor_dict


def getWorkUrls(url: str) -> tuple[str, list[Work]]:
    err, html = getHtml(url)
    if err:
        return err, []
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all(lambda tag: tag.name == 'tr' and\
                         'id' in tag.attrs)
    
    works = []
    for row in rows:
        work_url = ''
        title = ''
        if row.a and 'href' in row.a.attrs:
            work_url = row.a['href']
            if not work_url.startswith('http'):
                work_url = 'https://mydramalist.com' + work_url
        else:
            print('couldn\'t find url in', row)
            continue

        if row.a.span:
            title = row.a.span.text
        else:
            print('couldn\'t find title span in', row)
            continue

        works.append(Work(title, work_url))
    return '', works

def crawlWorkList(works: list, target_actors: dict[str, Actor], 
                  checkFn: lambda x: bool, progressFn: lambda x: None):
    """Go through works list and add roles to each actor in target_actors"""
    numDone = 0
    for work in works:
        if not checkFn():
            return
        progressFn(progressMessage(numDone, len(works), work.name))
        err, actors_dict = workUrlToActors(work.url)
        if err:
            progressFn(err)
            continue

        for actor_url, actor in actors_dict.items():
            if actor_url in target_actors:
                target_actors[actor_url].addRolesFrom(actor)
        numDone += 1

def crawlActorList(target_actors, work_urls):
    pass

def extractArbitraryWork(actor_dict: dict[str, Actor]) -> Work:
    if len(actor_dict) <= 0 or \
        len(next(iter(actor_dict.values())).roles) <= 0:
        return
    return next(iter(actor_dict.values())).roles[0].work

def sortByRoleType(actors):
    return sorted(actors, key = lambda a:
                  str(ROLE_VALUES[a.roles[0].type]) + a.name)

def intersect(target_url: str, list_url: str, checkFn=lambda x: bool,
                    progressFn=lambda x: None) -> list[Actor]:

    progressFn('Getting dramas')
    err, works = getWorkUrls(list_url)
    if err:
        progressFn(err)
        return []
    print('num works found', works)

    if not checkFn():
        return []
    progressFn('Getting casts')
    err, target_actors_dict = workUrlToActors(target_url)
    if err:
        progressFn(err)
        return []
    print('num actors found', target_actors_dict)
    
    target_work = extractArbitraryWork(target_actors_dict)
    if target_work and target_work.url in works:
        works_set = set(works)
        works_set.remove(target_work.url)
        works = list(works_set)
    print('works to crawl', works)
    crawlWorkList(works, target_actors_dict, checkFn, progressFn)
    # if len(works) < len(target_actors_dict):
    #     crawlWorkList(works, target_actors_dict, checkFn, progressFn)
    # else:
    #     crawlActorList(target_actors_dict, works)

    common_actors = [actor for actor in target_actors_dict.values() \
                     if len(actor.roles) > 1]
    return sortByRoleType(common_actors)

def intersectFake(arg1, arg2, checkFn, progressFn):
    total = 5
    for i in range(total + 1):
        if not checkFn():
            return []
        progressFn(progressMessage(i, total, 'a drama ' + str(i)))
        time.sleep(1)

    actor1 = Actor('Cao Yu Chen', 'caoyuchen.url')
    actor1.addRole(Work('The Blood of Youth', 'tboy.url'), 'Zhao Yu Zhen', 'Support')
    actor1.addRole(Work('The Untamed', 'theuntamed.url'), 'Jin Zi Xuan', 'Support')

    actor2 = Actor('Cheng Zi', 'chengzi.url')
    actor2.addRole(Work('The Blood of Youth', 'tboy.url'), 'Fairy Lady Rui', 'Support')
    actor2.addRole(Work('Love Between Fairy and Devil', 'lbfad.url'), 'Die Yi', 'Support')

    actor3 = Actor('Ding Yong Dai', 'dingyongdai.url')
    actor3.addRole(Work('The Blood of Youth', 'tboy.url'), 'Xiao Ruo Jin / Emperor Ming De', 'Main')
    actor3.addRole(Work('Nirvana in Fire', 'nif.url'), 'Emperor Xiao Xuan', 'Main')

    return sortByRoleType([actor1, actor2, actor3])

#intersect = intersectFake

if __name__ == '__main__':
    common_actors = intersect('https://mydramalist.com/683119-shao-nian-ge-xing', \
              'https://mydramalist.com/dramalist/mxticktock/completed')
    
    for actor in common_actors:
        print(actor.name, actor.roles)