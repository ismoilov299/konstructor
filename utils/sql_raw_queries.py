TOP_BOTS = """
select 
    bot.id, 
    bot.username,
    u.first_name owner,
    u.id owner_id,
    count(client.id) clients,
    m.balance balance,
    sum(o.bot_admin_profit) total_earned
from bot
join mainbotuser m on bot.owner_id=m.id
join public.user u on u.id = m.user_id
join clientbotuser client on client.bot_id=bot.id
join public.order o on o.user_id = client.id and o.status='Completed'
group by bot.id, u.id, m.id
order by total_earned desc
limit 200;
"""
