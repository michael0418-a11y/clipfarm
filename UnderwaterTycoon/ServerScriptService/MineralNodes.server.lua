-- MineralNodes.server.lua
-- Spawns clickable mineral/resource nodes on the ocean floor
-- Players click them to mine; nodes respawn after a cooldown
-- Place in ServerScriptService as a Script

local Players           = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Workspace         = game:GetService("Workspace")

local GameConfig = require(ReplicatedStorage:WaitForChild("GameConfig"))
local Remotes    = require(ReplicatedStorage:WaitForChild("RemoteEvents"))

local DataManager    -- lazy
local ResourceManager -- lazy

-- ── NODE DEFINITIONS ──────────────────────────────────────────────────────────

local NODE_TYPES = {
	{
		id       = "IronOre",
		label    = "Iron Ore",
		resource = "Minerals",
		amount   = { min = 8, max = 18 },
		color    = Color3.fromRGB(150, 100, 60),
		zone     = 1,
		respawn  = 30,
		size     = Vector3.new(4, 3, 4),
		count    = 25,
	},
	{
		id       = "CoralMineral",
		label    = "Coral Deposit",
		resource = "Minerals",
		amount   = { min = 5, max = 12 },
		color    = Color3.fromRGB(220, 120, 80),
		zone     = 1,
		respawn  = 20,
		size     = Vector3.new(3, 2, 3),
		count    = 20,
	},
	{
		id       = "DeepCrystal",
		label    = "Deep Crystal",
		resource = "Minerals",
		amount   = { min = 25, max = 55 },
		color    = Color3.fromRGB(100, 180, 255),
		zone     = 2,
		respawn  = 60,
		size     = Vector3.new(3, 5, 3),
		count    = 18,
	},
	{
		id       = "AbyssalOre",
		label    = "Abyssal Ore",
		resource = "Minerals",
		amount   = { min = 80, max = 160 },
		color    = Color3.fromRGB(60, 0, 120),
		zone     = 3,
		respawn  = 120,
		size     = Vector3.new(5, 6, 5),
		count    = 12,
	},
	{
		id       = "VoidCrystal",
		label    = "Void Crystal",
		resource = "Minerals",
		amount   = { min = 250, max = 500 },
		color    = Color3.fromRGB(20, 0, 60),
		zone     = 4,
		respawn  = 240,
		size     = Vector3.new(6, 8, 6),
		count    = 8,
	},
}

-- Zone depth ranges (Y positions)
local ZONE_Y = {
	{ yMin = -200,  yMax = -20   },
	{ yMin = -1000, yMax = -200  },
	{ yMin = -4000, yMax = -1000 },
	{ yMin = -5000, yMax = -4000 },
}

-- ── NODE INSTANCES ────────────────────────────────────────────────────────────

local nodesFolder = Instance.new("Folder", Workspace)
nodesFolder.Name  = "MineralNodes"

-- nodeData[part] = { type, respawnTime, isDepleted }
local nodeData    = {}
local respawnQueue = {}  -- { { part, timeRemaining } }

math.randomseed(os.time() + 42)

local function buildNode(nodeDef, position)
	local part           = Instance.new("Part", nodesFolder)
	part.Name            = nodeDef.id
	part.Size            = nodeDef.size
	part.Color           = nodeDef.color
	part.Anchored        = true
	part.CanCollide      = true
	part.Material        = Enum.Material.SmoothPlastic
	part.CFrame          = CFrame.new(position) *
		CFrame.Angles(math.random() * 0.4, math.random() * math.pi * 2, math.random() * 0.4)

	-- Billboard label
	local bb   = Instance.new("BillboardGui", part)
	bb.Size    = UDim2.new(0, 120, 0, 30)
	bb.StudsOffset = Vector3.new(0, nodeDef.size.Y / 2 + 1, 0)
	bb.MaxDistance = 30
	local lbl  = Instance.new("TextLabel", bb)
	lbl.Size   = UDim2.new(1, 0, 1, 0)
	lbl.BackgroundTransparency = 1
	lbl.Text   = "⛏ " .. nodeDef.label
	lbl.TextColor3 = Color3.new(1, 1, 1)
	lbl.TextScaled = true
	lbl.Font   = Enum.Font.GothamBold

	-- Attributes for client click detection
	part:SetAttribute("NodeId",   nodeDef.id)
	part:SetAttribute("Zone",     nodeDef.zone)
	part:SetAttribute("Resource", nodeDef.resource)
	part:SetAttribute("MinAmt",   nodeDef.amount.min)
	part:SetAttribute("MaxAmt",   nodeDef.amount.max)

	nodeData[part] = { def = nodeDef, isDepleted = false }
	return part
end

-- Spawn all nodes
for _, nodeDef in ipairs(NODE_TYPES) do
	local zoneY = ZONE_Y[nodeDef.zone]
	for i = 1, nodeDef.count do
		local angle  = math.random() * math.pi * 2
		local radius = math.random(30, 800)
		local x      = math.cos(angle) * radius
		local z      = math.sin(angle) * radius
		local y      = zoneY.yMin + math.random(0, math.abs(zoneY.yMax - zoneY.yMin) - 5)
		buildNode(nodeDef, Vector3.new(x, y, z))
	end
end

-- ── MINE REMOTE ───────────────────────────────────────────────────────────────

-- Client fires this when clicking a node
local MineNode = Instance.new("RemoteEvent")
MineNode.Name  = "MineNode"
MineNode.Parent = ReplicatedStorage:WaitForChild("Remotes")

MineNode.OnServerEvent:Connect(function(player, nodePart)
	-- Validate: is this actually a node?
	local data = nodePart and nodeData[nodePart]
	if not data or data.isDepleted then return end

	-- Validate: player must be close enough
	local char = player.Character
	if not char then return end
	local hrp  = char:FindFirstChild("HumanoidRootPart")
	if not hrp then return end
	local dist = (hrp.Position - nodePart.Position).Magnitude
	if dist > 20 then
		Remotes.Get("ResourceError"):FireClient(player, "Too far away to mine!")
		return
	end

	-- Check player has unlocked this zone
	local zoneRequired = nodePart:GetAttribute("Zone")
	if DataManager then
		local pdata = DataManager.Get(player)
		if pdata then
			local hasZone = false
			for _, z in ipairs(pdata.UnlockedZones) do
				if z >= zoneRequired then hasZone = true; break end
			end
			if not hasZone then
				Remotes.Get("ResourceError"):FireClient(player, "Unlock Zone " .. zoneRequired .. " to mine here!")
				return
			end
		end
	end

	-- Award resources
	local minAmt = nodePart:GetAttribute("MinAmt") or 5
	local maxAmt = nodePart:GetAttribute("MaxAmt") or 15
	local amount = math.random(minAmt, maxAmt)

	if ResourceManager then
		ResourceManager.MineNode(player, amount)
	end

	Remotes.Get("Notification"):FireClient(player, {
		title   = "⛏ Mined!",
		message = "+" .. amount .. " " .. (nodePart:GetAttribute("Resource") or "Minerals"),
		type    = "success",
	})

	-- Deplete node
	data.isDepleted       = true
	nodePart.Transparency = 0.7
	nodePart.Color        = Color3.fromRGB(80, 80, 80)

	local billboard = nodePart:FindFirstChildOfClass("BillboardGui")
	if billboard then billboard.Enabled = false end

	-- Queue respawn
	table.insert(respawnQueue, { part = nodePart, timer = data.def.respawn })
end)

-- ── RESPAWN LOOP ──────────────────────────────────────────────────────────────

local elapsed = 0
game:GetService("RunService").Heartbeat:Connect(function(dt)
	elapsed = elapsed + dt
	if elapsed < 1 then return end
	elapsed = 0

	local toRemove = {}
	for i, entry in ipairs(respawnQueue) do
		entry.timer = entry.timer - 1
		if entry.timer <= 0 then
			local part = entry.part
			local data = nodeData[part]
			if data then
				data.isDepleted   = false
				part.Transparency = 0
				part.Color        = data.def.color

				local billboard = part:FindFirstChildOfClass("BillboardGui")
				if billboard then billboard.Enabled = true end
			end
			table.insert(toRemove, i)
		end
	end
	for i = #toRemove, 1, -1 do
		table.remove(respawnQueue, toRemove[i])
	end
end)

task.defer(function()
	DataManager     = require(script.Parent:WaitForChild("DataManager"))
	ResourceManager = require(script.Parent:WaitForChild("ResourceManager"))
end)

print("[MineralNodes] Nodes spawned.")
