# Nutrition

Nutrition is one of the pillars of our physical and metal health. Other pillars are sleep, social connections, and copious amount of trail running.  
There is a huge body of knowledge on nutrition on the Internet, you've gotten time and curiosity - you have all the tools for making that pillar shinier and stronger.  

For years, I've kept a short log of everything I eat throughout a day. Mainly for the sake of drawing correlations between what comes in and how I feel on a given day.
Be it energy levels, indigestion, or other signals from my body I find interesting. I keep the food descriptions in the "free-form" - I couldn't bother more writing precise numbers and portion sizes.
If that simple journaling has delivered expected but also surprising benefits.

My next big interest was in better understanding my hunger. Why, on some days, I feel satiated for hours after a meal, while on the other days I'm seemingly unable to tame my appetite - even though the exertion levels and
foods consumed were at a comparable levels. While there is a whole science behind hunger and its mechanisms, the obvious thing about satiety is that you feel full for prolonged periods of time when there is a good balance
in what you ate earlier. Like amount of fiber, ratio of proteins to carbs, fats, sugars, and such. I've always been confident that I consume healthy and simple foods (cooking your own meals helps!) almost all the time. However,
are those meals balanced?

Do you know what you eat?

# tune-your-nutrition

This a small utility I regularly use myself. It reads my daily notes I take in [Obsidian](https://obsidian.md/), extracts food descriptions from a note, runs them through a LLM, and writes back a nutrition breakdown table in
a separate file. It then links (using Obsidian's [links](https://help.obsidian.md/links)) the food description in the note to its respective table for easy navigation. It also keep tracks of daily intake in a
separate table in the same file. The tool can analyze food descriptions with Claude or Grok models. I find them comparable in most cases, but the Grok LLM seems to be more reliable for this particular use case.

The tool relies on special markers to determine what part of a note is a food description. E.g., `==breakfast==` and all the lines below it; a new line acts as an end of the description.

The way the tools works is heavily inspired by my own workflow, obviously. The main goal of sharing it publicly is a) some companies want to see what you're working on in free time b) I find the tool and overall approach quite useful, if it inspires at least one person - it'd be great.

## automation

Obsidian has pretty good synchronization functionality. You type a note on one device, and it gets propagated to all other devices you have Obsidian on. Unfortunately, there is not public API to query files being synced
(or retrieve their content). I wanted my tool to run somewhere in the background, and the ability to type notes on any of my devices and get nutrition breakdown synced to all devices automatically. I came with a pretty simple
setup that costs $4/mo (a price for a Digital Ocean droplet). I have:

1. Always online server (the aforementioned droplet)
2. My MacBook with Obsidian
3. My Android phone with Obsidian

All three "devices" are running the amazing and free [syncthing](https://syncthing.net/). When I edit a note on any of my devices, it gets propagated to all other devices.
The droplet has a cron job that runs the tool on daily notes every once in a while. When the tools processes a new food description and generates/update a breakdown (in a different file) -> it get synced to my phone and MacBook.
