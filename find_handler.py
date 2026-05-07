lines = open('local/tg_webhook_server.py', encoding='utf-8').readlines()
for i, l in enumerate(lines):
    if 'handler(args)' in l:
        print(f'{i+1}: {l}', end='')
