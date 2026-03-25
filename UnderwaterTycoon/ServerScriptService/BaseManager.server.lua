-- BaseManager.server.lua
-- Handles placing, upgrading, removing base modules in the world
-- Place in ServerScriptService as a ModuleScript

local Players           = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace         = game:GetService("Workspace")

local GameConfig  = require(ReplicatedStorage:WaitForChild("GameConfig"))
local ModuleData  = require(ReplicatedStorage:WaitForChild("Modules"):WaitForChild("ModuleData"))
local Remotes     = require(ReplicatedStorage:WaitForChild("RemoteEvents"))

local DataManager    -- lazy-loaded
local CombatManager  -- lazy-loaded

local BaseManager = {}

-- Folder in Workspace where all base parts live
local basesFolder = Workspace:FindFirstChild("Bases") or Instance.new("Folder", Workspace)
basesFolder.Name  = "Bases"

-- [userId] → Folder of their base parts
local playerFolders = {}

-- [partInstance] → { userId, moduleIndex }  (for quick lookup on damage)
local partToModule  = {}

-- ── FOLDER SETUP ─────────────────────────────────────────────────────────────

local function getPlayerFolder(player)
	if playerFolders[player.UserId] then
		return playerFolders[player.UserId]
	end
	local folder = Instance.new("Folder")
	folder.Name  = tostring(player.UserId)
	folder.Parent = basesFolder
	playerFolders[player.UserId] = folder
	return folder
end

-- ── BUILD A PART FOR A MODULE ─────────────────────────────────────────────────

local function buildModulePart(modDef, position, rotation, level, instanceId)
	local part        = Instance.new("Part")
	part.Name         = modDef.id .. "_" .. instanceId
	part.Size         = modDef.size
	part.Color        = modDef.color
	part.Anchored     = true
	part.CastShadow   = false
	part.Material     = Enum.Material.SmoothPlastic
	part.CFrame       = CFrame.new(position) * CFrame.Angles(0, math.rad(rotation or 0), 0)

	-- Label
	local billboard       = Instance.new("BillboardGui", part)
	billboard.Size        = UDim2.new(0, 120, 0, 40)
	billboard.StudsOffset = Vector3.new(0, modDef.size.Y / 2 + 1, 0)
	billboard.AlwaysOnTop = false
	local label           = Instance.new("TextLabel", billboard)
	label.Size            = UDim2.new(1, 0, 1, 0)
	label.BackgroundTransparency = 1
	label.Text            = modDef.displayName .. " (Lv." .. level .. ")"
	label.TextColor3      = Color3.new(1, 1, 1)
	label.TextScaled      = true

	-- HP bar (for combat damage)
	local hpBar           = Instance.new("SelectionBox", part)  -- placeholder
	-- (Full HP bar UI handled in client HUD)

	-- Attribute storage
	part:SetAttribute("ModuleId",    modDef.id)
	part:SetAttribute("InstanceId",  instanceId)
	part:SetAttribute("Level",       level)
	part:SetAttribute("MaxHP",       100 * level)
	part:SetAttribute("CurrentHP",   100 * level)

	return part
end

-- ── PLACE STARTER POD ────────────────────────────────────────────────────────

function BaseManager.PlaceStarterPod(player)
	local data   = DataManager.Get(player)
	local modDef = ModuleData.Get("StarterPod")
	local pos    = Vector3.new(0, -10, 0)  -- just below surface
	local instanceId = "pod_" .. player.UserId

	local entry = {
		id         = "StarterPod",
		position   = { pos.X, pos.Y, pos.Z },
		rotation   = 0,
		level      = 1,
		instanceId = instanceId,
		hp         = 100,
	}
	table.insert(data.PlacedModules, entry)

	local folder = getPlayerFolder(player)
	local part   = buildModulePart(modDef, pos, 0, 1, instanceId)
	part.Parent  = folder
	partToModule[part] = { userId = player.UserId, instanceId = instanceId }

	Remotes.Get("ModulePlaced"):FireClient(player, entry)
end

-- ── RESTORE BASE ─────────────────────────────────────────────────────────────

function BaseManager.RestoreBase(player)
	local data   = DataManager.Get(player)
	local folder = getPlayerFolder(player)

	for _, entry in ipairs(data.PlacedModules) do
		local modDef = ModuleData.Get(entry.id)
		if not modDef then continue end
		local pos  = Vector3.new(entry.position[1], entry.position[2], entry.position[3])
		local part = buildModulePart(modDef, pos, entry.rotation or 0, entry.level or 1, entry.instanceId)
		part.Parent = folder
		partToModule[part] = { userId = player.UserId, instanceId = entry.instanceId }
	end
end

-- ── PLACE MODULE (from client request) ───────────────────────────────────────

Remotes.Get("PlaceModule").OnServerEvent:Connect(function(player, moduleId, posTable, rotation)
	local data   = DataManager.Get(player)
	if not data then return end

	local modDef = ModuleData.Get(moduleId)
	if not modDef then
		Remotes.Get("ResourceError"):FireClient(player, "Unknown module: " .. tostring(moduleId))
		return
	end

	-- Zone check
	local highestZone = data.UnlockedZones[#data.UnlockedZones] or 1
	if modDef.requiredZone > highestZone then
		Remotes.Get("ResourceError"):FireClient(player, "Unlock " .. GameConfig.Zones[modDef.requiredZone].name .. " first!")
		return
	end

	-- Module limit
	if #data.PlacedModules >= GameConfig.Settings.MaxModulesPerPlayer then
		Remotes.Get("ResourceError"):FireClient(player, "Module limit reached (" .. GameConfig.Settings.MaxModulesPerPlayer .. ")")
		return
	end

	-- Cost check
	if not DataManager.CanAfford(player, modDef.cost) then
		Remotes.Get("ResourceError"):FireClient(player, "Not enough resources!")
		return
	end

	-- Deduct cost
	DataManager.Deduct(player, modDef.cost)

	-- Create entry
	local instanceId = moduleId .. "_" .. player.UserId .. "_" .. os.time() .. "_" .. math.random(1000, 9999)
	local pos = Vector3.new(posTable[1], posTable[2], posTable[3])

	local entry = {
		id         = moduleId,
		position   = posTable,
		rotation   = rotation or 0,
		level      = 1,
		instanceId = instanceId,
		hp         = 100,
	}
	table.insert(data.PlacedModules, entry)

	-- Build world part
	local folder = getPlayerFolder(player)
	local part   = buildModulePart(modDef, pos, rotation or 0, 1, instanceId)
	part.Parent  = folder
	partToModule[part] = { userId = player.UserId, instanceId = instanceId }

	Remotes.Get("ModulePlaced"):FireClient(player, entry)
end)

-- ── UPGRADE MODULE ────────────────────────────────────────────────────────────

Remotes.Get("UpgradeModule").OnServerEvent:Connect(function(player, instanceId)
	local data = DataManager.Get(player)
	if not data then return end

	local entry = nil
	local entryIndex = nil
	for i, e in ipairs(data.PlacedModules) do
		if e.instanceId == instanceId then
			entry      = e
			entryIndex = i
			break
		end
	end
	if not entry then return end

	local modDef  = ModuleData.Get(entry.id)
	if not modDef then return end

	local curLevel = entry.level or 1
	if curLevel >= modDef.maxLevel then
		Remotes.Get("ResourceError"):FireClient(player, "Already at max level!")
		return
	end

	local nextLevel = curLevel + 1
	local cost      = modDef.upgradeCost and modDef.upgradeCost[nextLevel]
	if not cost then return end

	if not DataManager.CanAfford(player, cost) then
		Remotes.Get("ResourceError"):FireClient(player, "Not enough resources to upgrade!")
		return
	end

	DataManager.Deduct(player, cost)
	entry.level = nextLevel
	entry.hp    = 100 * nextLevel

	-- Update world part label
	local folder = getPlayerFolder(player)
	for _, part in ipairs(folder:GetChildren()) do
		if part:GetAttribute("InstanceId") == instanceId then
			part:SetAttribute("Level",     nextLevel)
			part:SetAttribute("MaxHP",     100 * nextLevel)
			part:SetAttribute("CurrentHP", 100 * nextLevel)
			local bg = part:FindFirstChildOfClass("BillboardGui")
			if bg then
				local lbl = bg:FindFirstChildOfClass("TextLabel")
				if lbl then
					lbl.Text = modDef.displayName .. " (Lv." .. nextLevel .. ")"
				end
			end
		end
	end

	Remotes.Get("ModuleUpgraded"):FireClient(player, instanceId, nextLevel)
end)

-- ── REMOVE MODULE ─────────────────────────────────────────────────────────────

Remotes.Get("RemoveModule").OnServerEvent:Connect(function(player, instanceId)
	local data = DataManager.Get(player)
	if not data then return end

	-- Don't allow removing starter pod
	for i, entry in ipairs(data.PlacedModules) do
		if entry.instanceId == instanceId then
			if entry.id == "StarterPod" then
				Remotes.Get("ResourceError"):FireClient(player, "Cannot remove your Starter Pod!")
				return
			end
			-- Refund 50%
			local modDef = ModuleData.Get(entry.id)
			if modDef and modDef.cost then
				for resource, amount in pairs(modDef.cost) do
					DataManager.AddResource(player, resource, math.floor(amount * 0.5))
				end
			end
			table.remove(data.PlacedModules, i)
			break
		end
	end

	-- Remove world part
	local folder = getPlayerFolder(player)
	for _, part in ipairs(folder:GetChildren()) do
		if part:GetAttribute("InstanceId") == instanceId then
			partToModule[part] = nil
			part:Destroy()
			break
		end
	end

	Remotes.Get("ModuleRemoved"):FireClient(player, instanceId)
end)

-- ── TAKE DAMAGE (called by CombatManager) ─────────────────────────────────────

function BaseManager.DamageModule(player, instanceId, amount)
	local data = DataManager.Get(player)
	if not data then return end

	for _, entry in ipairs(data.PlacedModules) do
		if entry.instanceId == instanceId then
			entry.hp = math.max(0, (entry.hp or 100) - amount)
			Remotes.Get("ModuleDamaged"):FireClient(player, instanceId, entry.hp)

			if entry.hp <= 0 then
				-- Module destroyed
				Remotes.Get("ModuleDestroyed"):FireClient(player, instanceId)
				Remotes.Get("BaseUnderAttack"):FireClient(player)
				-- Remove from data and world
				Remotes.Get("RemoveModule"):Fire(player, instanceId)
			end
			return
		end
	end
end

-- ── GET ALL BASE PARTS (for CombatManager targeting) ─────────────────────────

function BaseManager.GetBaseParts(player)
	local folder = playerFolders[player.UserId]
	if not folder then return {} end
	return folder:GetChildren()
end

-- ── REMOTE: GET BASE LAYOUT ───────────────────────────────────────────────────

Remotes.Get("GetBaseLayout").OnServerInvoke = function(player)
	local data = DataManager.Get(player)
	return data and data.PlacedModules or {}
end

-- Lazy-loads
task.defer(function()
	DataManager   = require(script.Parent:WaitForChild("DataManager"))
	CombatManager = require(script.Parent:WaitForChild("CombatManager"))
end)

return BaseManager
