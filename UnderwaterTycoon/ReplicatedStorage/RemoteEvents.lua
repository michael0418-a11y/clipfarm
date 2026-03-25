-- RemoteEvents.lua
-- Creates all RemoteEvents and RemoteFunctions on the server
-- Place in ReplicatedStorage as a Script (runs once on server start)
-- Then require this from other scripts to get references cleanly

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local RemoteEvents = {}

-- List of all RemoteEvent names
local EVENT_NAMES = {
	-- Mode selection
	"SelectMode",          -- client → server: "Solo" or "Multiplayer"
	"ModeConfirmed",       -- server → client: mode was accepted

	-- Building
	"PlaceModule",         -- client → server: moduleId, position, rotation
	"UpgradeModule",       -- client → server: moduleInstanceId
	"RemoveModule",        -- client → server: moduleInstanceId
	"ModulePlaced",        -- server → client: confirmation + data
	"ModuleUpgraded",      -- server → client: new level
	"ModuleRemoved",       -- server → client: instanceId

	-- Resources
	"ResourceUpdate",      -- server → client: full resource table
	"ResourceError",       -- server → client: "Not enough Minerals" etc.

	-- Zones
	"UnlockZone",          -- client → server: zoneIndex
	"ZoneUnlocked",        -- server → client: zoneIndex

	-- Combat
	"CreatureSpawned",     -- server → client: creature data + position
	"CreatureDied",        -- server → client: creatureId, reward
	"BaseUnderAttack",     -- server → client: alert
	"ModuleDamaged",       -- server → client: moduleId, newHp
	"ModuleDestroyed",     -- server → client: moduleId

	-- Player
	"PlayerDiving",        -- client → server: isDiving bool
	"PlayerDepthUpdate",   -- server → client: current depth

	-- Notifications
	"Notification",        -- server → client: { title, message, type }

	-- Persistence
	"DataSaved",           -- server → client: save confirmed
}

-- List of all RemoteFunction names
local FUNCTION_NAMES = {
	"GetPlayerData",       -- client → server: returns full save data
	"GetBaseLayout",       -- client → server: returns all placed modules
	"CanAfford",           -- client → server: moduleId, returns bool
}

-- Create or find folder
local folder = ReplicatedStorage:FindFirstChild("Remotes")
if not folder then
	folder = Instance.new("Folder")
	folder.Name = "Remotes"
	folder.Parent = ReplicatedStorage
end

-- Create RemoteEvents
for _, name in ipairs(EVENT_NAMES) do
	if not folder:FindFirstChild(name) then
		local re = Instance.new("RemoteEvent")
		re.Name = name
		re.Parent = folder
	end
	RemoteEvents[name] = folder:FindFirstChild(name)
end

-- Create RemoteFunctions
for _, name in ipairs(FUNCTION_NAMES) do
	if not folder:FindFirstChild(name) then
		local rf = Instance.new("RemoteFunction")
		rf.Name = name
		rf.Parent = folder
	end
	RemoteEvents[name] = folder:FindFirstChild(name)
end

-- Convenience getter
function RemoteEvents.Get(name)
	return folder:FindFirstChild(name)
end

return RemoteEvents
