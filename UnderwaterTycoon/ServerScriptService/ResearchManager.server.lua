-- ResearchManager.server.lua
-- Handles spending ResearchPoints to unlock research tree nodes
-- Effects are applied by ResourceManager / CombatManager reading player data
-- Place in ServerScriptService

local Players           = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local ResearchData = require(ReplicatedStorage:WaitForChild("Modules"):WaitForChild("ResearchData"))
local Remotes      = require(ReplicatedStorage:WaitForChild("RemoteEvents"))

local DataManager -- lazy

local ResearchManager = {}

-- ── REMOTE: BUY RESEARCH ──────────────────────────────────────────────────────

local BuyResearch = Instance.new("RemoteEvent")
BuyResearch.Name  = "BuyResearch"
BuyResearch.Parent = ReplicatedStorage:WaitForChild("Remotes")

local ResearchUpdate = Instance.new("RemoteEvent")
ResearchUpdate.Name  = "ResearchUpdate"
ResearchUpdate.Parent = ReplicatedStorage:WaitForChild("Remotes")

BuyResearch.OnServerEvent:Connect(function(player, researchId)
	local resNode = ResearchData.Get(researchId)
	if not resNode then return end

	local data = DataManager and DataManager.Get(player)
	if not data then return end

	-- Already unlocked?
	data.UnlockedResearch = data.UnlockedResearch or {}
	for _, id in ipairs(data.UnlockedResearch) do
		if id == researchId then
			Remotes.Get("ResourceError"):FireClient(player, "Already researched!")
			return
		end
	end

	-- Check prerequisites
	for _, req in ipairs(resNode.requires) do
		local hasReq = false
		for _, id in ipairs(data.UnlockedResearch) do
			if id == req then hasReq = true; break end
		end
		if not hasReq then
			local reqNode = ResearchData.Get(req)
			Remotes.Get("ResourceError"):FireClient(player,
				"Requires: " .. (reqNode and reqNode.displayName or req))
			return
		end
	end

	-- Cost check
	if (data.ResearchPoints or 0) < resNode.cost then
		Remotes.Get("ResourceError"):FireClient(player,
			"Need " .. resNode.cost .. " Research Points (have " .. math.floor(data.ResearchPoints or 0) .. ")")
		return
	end

	-- Deduct and unlock
	data.ResearchPoints = data.ResearchPoints - resNode.cost
	table.insert(data.UnlockedResearch, researchId)

	ResearchUpdate:FireClient(player, data.UnlockedResearch)
	Remotes.Get("Notification"):FireClient(player, {
		title   = "Research Complete!",
		message = resNode.displayName .. " unlocked!",
		type    = "success",
	})
end)

-- ── REMOTE: GET RESEARCH STATE ────────────────────────────────────────────────

local GetResearch = Instance.new("RemoteFunction")
GetResearch.Name  = "GetResearch"
GetResearch.Parent = ReplicatedStorage:WaitForChild("Remotes")

GetResearch.OnServerInvoke = function(player)
	local data = DataManager and DataManager.Get(player)
	return data and data.UnlockedResearch or {}
end

-- ── APPLY EFFECT HELPERS (used by other managers) ────────────────────────────

function ResearchManager.HasResearch(player, researchId)
	local data = DataManager and DataManager.Get(player)
	if not data then return false end
	data.UnlockedResearch = data.UnlockedResearch or {}
	for _, id in ipairs(data.UnlockedResearch) do
		if id == researchId then return true end
	end
	return false
end

function ResearchManager.GetProductionMultiplier(player, moduleId)
	local data = DataManager and DataManager.Get(player)
	if not data then return 1 end
	local mult = 1
	for _, resId in ipairs(data.UnlockedResearch or {}) do
		local node = ResearchData.Get(resId)
		if node and node.effect.type == "ProductionBoost" and node.effect.module == moduleId then
			mult = mult * node.effect.multiplier
		end
	end
	return mult
end

function ResearchManager.GetOxygenDrainMultiplier(player)
	local data = DataManager and DataManager.Get(player)
	if not data then return 1 end
	local reduction = 0
	for _, resId in ipairs(data.UnlockedResearch or {}) do
		local node = ResearchData.Get(resId)
		if node and node.effect.type == "OxygenDrainReduction" then
			reduction = reduction + node.effect.percent
		end
	end
	return math.max(0.1, 1 - reduction)
end

function ResearchManager.GetSpawnRateMultiplier(player)
	local data = DataManager and DataManager.Get(player)
	if not data then return 1 end
	local reduction = 0
	for _, resId in ipairs(data.UnlockedResearch or {}) do
		local node = ResearchData.Get(resId)
		if node and node.effect.type == "SpawnRateReduction" then
			reduction = reduction + node.effect.percent
		end
	end
	return math.max(0.2, 1 - reduction)
end

task.defer(function()
	DataManager = require(script.Parent:WaitForChild("DataManager"))
end)

return ResearchManager
