from http_json import http_method
import argparse
import sys

MIN_SKILL = 1000
MAX_SKILL = 100000
AVG_SKILL = 40000
STD_SKILL = 20000
D = MAX_SKILL - MIN_SKILL

TOKEN = ""
BASE_URL = "https://huqeyhi95c.execute-api.ap-northeast-2.amazonaws.com/prod"
WAIT_WEIGHT = 3

problem_info = {
    1 : {"num_users" : 30, "avg_match" : 1},
    2 : {"num_users" : 900, "avg_match" : 45}
}

get_method = lambda url, print_status=False: http_method("GET", BASE_URL, sub_url=url, token=TOKEN, print_status=print_status)
post_method = lambda url , data : http_method("POST", BASE_URL, sub_url=url, data=data, token=TOKEN)
put_method = lambda url , data : http_method("PUT", BASE_URL, sub_url=url, data=data, token=TOKEN)


### APIs ###

def api_start(problem, init_token):
    assert 1 <= problem <= 2
    resp = http_method("POST", BASE_URL, "/start", data={'problem':problem}, token=init_token, init=True, print_status=True)
    print("Server has started:")
    print(resp)
    if type(resp) is dict:
        return resp.get('auth_key', "")
        # return empty sting if auth_key does not exist
    return ""

def api_score():
    return get_method("/score", print_status=True)

def api_waiting_line(current_time):
    resp = get_method("/waiting_line").get("waiting_line", [])
    return [(data['id'], current_time - data['from']) for data in resp]

def api_game_result():
    resp = get_method("/game_result").get("game_result", [])
    return [(data['win'], data['lose'], data['taken']) for data in resp]

def api_match(data):
    return put_method("/match", {"pairs" : data})

def api_user_info():
    resp = get_method("/user_info").get("user_info", [])
    return [(data['id'], data['grade']) for data in resp]

def api_match(data):
    return put_method("/match", {"pairs" : data})

def api_change_grade(skills, num_users):
    l = sorted([x for x in range(1, num_users + 1)], key=lambda x: skills[x])
    commands = [{'id' : l[idx], 'grade' : idx} for idx in range(num_users)]
    return put_method("/change_grade", {"commands" : commands})


### Functions ###

def update_skills(skills, win_id, lose_id, elapsed_time):
    skill_diff = (40 - elapsed_time) / 35 * 99000 # E[e] = 0
    
    # ELO Update - credit: kakao solutoins
    prob = skills[win_id] / (skills[win_id] + skills[lose_id])
    factor = skill_diff - (skills[win_id] - skills[lose_id])
    win_update, lose_update = factor * (1 - prob) / 2, factor * (0 - prob) / 2

    skills[win_id] = min(skills[win_id] + win_update / 2, MAX_SKILL)
    skills[lose_id] = max(skills[lose_id] + lose_update / 2, MIN_SKILL)

    return skills


def solve(data):
    # (T * O(|results| + |WL| log |WL|) + O(num_users)) * T_api_call
    # O(T * N log N) * T_api_call where N = num_users
    # Scenario 1: 595 * 30 * lg 30 ~ 90,000 api calls
    # Scenario 2: 595 * 900 * lg (900) ~ 5,000,000 api calls
    problem, init_token = data["problem"], data["init_token"]
    print(problem, init_token)
    global TOKEN
    TOKEN = api_start(problem, init_token)
    num_users = problem_info[problem]["num_users"]

    skills = { id : AVG_SKILL for id in range(1, num_users + 1) }

    # T * O(|results| + |WL| log |WL|)
    for current_time in range(596):
        results = api_game_result()

        # O(|results|)
        for result in results:
            # update skills
            win_id, lose_id, elapsed_time = result
            skills = update_skills(skills, win_id, lose_id, elapsed_time)

        # O(|waiting_line| log |waiting_line|)
        waiting_line = api_waiting_line(current_time)
        waiting_line = sorted(waiting_line, key=lambda x: x[0] * WAIT_WEIGHT * x[1], reverse=True)

        idx = 0
        pairs = []
        remaining = []

        # O(|waiting_line|)
        while idx < len(waiting_line) - 1:
            a, b = waiting_line[idx][0], waiting_line[idx + 1][0]

            if abs(skills[a] - skills[b]) <= STD_SKILL:
                # match a and b
                pairs.append((a, b))
                idx += 2
            else:
                # TODO: compare idx w/ remaining users in the previous line
                if len(remaining) > 0:
                    c = remaining[-1]
                    if abs(skills[c] - skills[a]) <= STD_SKILL:
                        pairs.append((a, c))
                        remaining.pop()
                    else:
                        remaining.append(a)
                else:
                    remaining.append(a)
                idx += 1
                    
        api_match(pairs)

        if current_time % 20 == 0:
            print(f"Problem {problem}: time = {current_time}")
            sys.stdout.flush()

    for id in range(1, num_users + 1):
        skills[id] = int(skills[id])
    api_change_grade(skills, num_users)
    api_match([])
    return api_score()
    
if __name__ == "__main__":
    for problem in [1, 2]:
        data = {
            "problem": problem,
            "init_token": "86aff322c0e9b10f0bfb5c3dd1b34963"
        }
        print(f"Score: {solve(data)}")

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--problem", type=int, default=1)
#     parser.add_argument("--init_token", type=str, required=True)
#     parser.add_argument("--base_url", type=str, required=True)
#     parser.add_argument("--match_skill", type=int, default=STD_SKILL) # max diff of skills b/w two users that are in a match
#     parser.add_argument("--wait_weight", type=int, default=3) # weight for wait time in the queue
#     args = parser.parse_args()

#     print(f"Score: {solve(args)}")