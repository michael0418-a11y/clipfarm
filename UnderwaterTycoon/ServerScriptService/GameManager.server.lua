-- GameManager.server.lua
-- Core server logic: player joining, mode selection, notifications
-- Place in ServerScriptService

local Players           = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ServerStorage     = game:GetService("ServerStorage")

local GameConfig   = require(ReplicatedStorage:WaitForChild("GameConfig"))
local Remotes      = require(ReplicatedStorage:WaitForChild("RemoteEvents"))

-- Wait for DataManager (also lives in ServerScriptService)
local DataManager  = require(script.Parent:WaitForChild("DataManager"))
local BaseManager  = require(script.Parent:WaitForChild("BaseManager"))
local ResourceManager = require(script.Parent:WaitForChild("ResourceManager"))

local GameManager  = {}

-- Tracks which players have chosen a mode
local modeSelected = {}

-- ── HELPERS ──────────────────────────────────────────────────────────────────

local function notify(player, title, message, notifType)
	-- notifType: "info" | "success" | "warning" | "danger"
	Remotes.Get("Notification"):FireClient(player, {
		title   = title,
		message = message,
		type    = notifType or "info",
	})
end

local function sendResources(player)
	local data = DataManager.Get(player)
	if not data then return end
	Remotes.Get("ResourceUpdate"):FireClient(player, {
		Minerals       = data.Minerals,
		Oxygen         = data.Oxygen,
		Food           = data.Food,
		Power          = data.Power,
		Coins          = data.Coins,
		ResearchPoints = data.ResearchPoints,
	})
end

-- ── SPAWN ─────────────────────────────────────────────────────────────────────

local function spawnPlayerAtSurface(player)
	local character = player.Character or player.CharacterAdded:Wait()
	local hrp = character:WaitForChild("HumanoidRootPart")
	-- Place player on the surface boat / spawn platform (adjust CFrame as needed)
	hrp.CFrame = CFrame.new(0, 20, 0)
end

-- ── MODE SELECTION ────────────────────────────────────────────────────────────

Remotes.Get("SelectMode").OnServerEvent:Connect(function(player, mode)
	if modeSelected[player.UserId] then return end  -- already chosen
	if mode ~= "Solo" and mode ~= "Multiplayer" then return end

	local data = DataManager.Get(player)
	if not data then return end

	data.GameMode = mode
	modeSelected[player.UserId] = true

	Remotes.Get("ModeConfirmed"):FireClient(player, mode)

	-- Spawn the starter pod for new players
	if #data.PlacedModules == 0 then
		BaseManager.PlaceStarterPod(player)
	else
		-- Restore existing base layout
		BaseManager.RestoreBase(player)
	end

	-- Start AFK resource generation for this player
	ResourceManager.StartForPlayer(player)

	-- Send initial resource state
	sendResources(player)

	notify(player, "Welcome!", "Your underwater adventure begins. Dive in!", "success")
end)

-- ── PLAYER JOINED ────────────────────────────────────────────────────────────

Players.PlayerAdded:Connect(function(player)
	-- Data is loaded by DataManager automatically
	-- Wait a moment then show mode select screen
	task.delay(1, function()
		if player and player.Parent then
			-- The client ModeSelectGui fires SelectMode when player picks
			-- Nothing needed here server-side yet
		end
	end)

	player.CharacterAdded:Connect(function(character)
		spawnPlayerAtSurface(player)

		-- Restore diving state / depth tracking
		character:WaitForChild("Humanoid").Died:Connect(function()
			task.delay(3, function()
				player:LoadCharacter()
			end)
		end)
	end)
end)

-- ── PLAYER LEAVING ────────────────────────────────────────────────────────────

Players.PlayerRemoving:Connect(function(player)
	modeSelected[player.UserId] = nil
	ResourceManager.StopForPlayer(player)
end)

-- ── REMOTE: GET PLAYER DATA ───────────────────────────────────────────────────

Remotes.Get("GetPlayerData").OnServerInvoke = function(player)
	return DataManager.Get(player)
end

-- ── REMOTE: CAN AFFORD ───────────────────────────────────────────────────────

Remotes.Get("CanAfford").OnServerInvoke = function(player, costs)
	return DataManager.CanAfford(player, costs)
end

-- ── REMOTE: GET LEADERBOARD ───────────────────────────────────────────────────
-- Returns public stats for all players for the leaderboard GUI

local GetLeaderboard = Instance.new("RemoteFunction")
GetLeaderboard.Name   = "GetLeaderboard"
GetLeaderboard.Parent = game:GetService("ReplicatedStorage"):WaitForChild("Remotes")

GetLeaderboard.OnServerInvoke = function(_player)
	local result = {}
	for _, p in ipairs(Players:GetPlayers()) do
		local data = DataManager.Get(p)
		local char = p.Character
		local hrp  = char and char:FindFirstChild("HumanoidRootPart")
		table.insert(result, {
			name            = p.Name,
			Coins           = data and data.Coins or 0,
			CreaturesKilled = data and data.CreaturesKilled or 0,
			Depth           = hrp and math.max(0, math.floor(-hrp.Position.Y)) or 0,
		})
	end
	return result
end

-- ── PERIODIC RESOURCE BROADCAST ───────────────────────────────────────────────
-- Push updated resource totals to all clients every 5 seconds

task.spawn(function()
	while true do
		task.wait(5)
		for _, player in ipairs(Players:GetPlayers()) do
			sendResources(player)
		end
	end
end)

return GameManager
