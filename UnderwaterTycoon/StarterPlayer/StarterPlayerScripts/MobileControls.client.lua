-- MobileControls.client.lua
-- On-screen touch buttons for mobile players: dive down, swim up, mine, shoot
-- Place in StarterPlayer/StarterPlayerScripts as a LocalScript

local Players          = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")
local RunService       = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Remotes = require(ReplicatedStorage:WaitForChild("RemoteEvents"))
local player  = Players.LocalPlayer

-- Only show on touch devices
if not UserInputService.TouchEnabled then return end

-- Wait for PlayerGui
local playerGui = player:WaitForChild("PlayerGui")

-- ── SCREEN GUI ────────────────────────────────────────────────────────────────

local mobileGui        = Instance.new("ScreenGui", playerGui)
mobileGui.Name         = "MobileControls"
mobileGui.ResetOnSpawn = false
mobileGui.ZIndex       = 10

-- ── BUTTON FACTORY ────────────────────────────────────────────────────────────

local function makeButton(parent, name, text, xPct, yPct, size, color)
	local btn            = Instance.new("TextButton", parent)
	btn.Name             = name
	btn.Size             = UDim2.new(0, size, 0, size)
	btn.Position         = UDim2.new(xPct, -size / 2, yPct, -size / 2)
	btn.BackgroundColor3 = color
	btn.BackgroundTransparency = 0.3
	btn.Text             = text
	btn.TextColor3       = Color3.new(1, 1, 1)
	btn.TextScaled       = true
	btn.Font             = Enum.Font.GothamBold
	btn.ZIndex           = 11
	local corner         = Instance.new("UICorner", btn)
	corner.CornerRadius  = UDim.new(1, 0)
	-- Stroke
	local stroke         = Instance.new("UIStroke", btn)
	stroke.Color         = Color3.new(1, 1, 1)
	stroke.Transparency  = 0.5
	stroke.Thickness     = 2
	return btn
end

-- ── DIVE BUTTONS (bottom right cluster) ──────────────────────────────────────

local diveUp   = makeButton(mobileGui, "DiveUp",   "▲",  0.88, 0.75, 70, Color3.fromRGB(0, 140, 220))
local diveDown = makeButton(mobileGui, "DiveDown", "▼",  0.88, 0.88, 70, Color3.fromRGB(0, 80, 160))

-- ── MINE BUTTON (bottom center-right) ────────────────────────────────────────

local mineBtn  = makeButton(mobileGui, "Mine",  "⛏",  0.75, 0.88, 70, Color3.fromRGB(160, 100, 40))

-- ── SHOOT BUTTON (bottom center) ─────────────────────────────────────────────

local shootBtn = makeButton(mobileGui, "Shoot", "🔴",  0.63, 0.88, 70, Color3.fromRGB(180, 30, 30))

-- ── BUILD TOGGLE (bottom left-ish) ───────────────────────────────────────────

local buildBtn = makeButton(mobileGui, "Build", "🔧",  0.12, 0.88, 70, Color3.fromRGB(40, 120, 200))

-- ── HOLD STATE ────────────────────────────────────────────────────────────────

local holdUp    = false
local holdDown  = false

-- Dive Up (hold)
diveUp.MouseButton1Down:Connect(function()  holdUp   = true  end)
diveUp.MouseButton1Up:Connect(function()    holdUp   = false end)
diveUp.TouchLongPress:Connect(function()    holdUp   = true  end)

diveDown.MouseButton1Down:Connect(function() holdDown = true  end)
diveDown.MouseButton1Up:Connect(function()   holdDown = false end)
diveDown.TouchLongPress:Connect(function()   holdDown = true  end)

-- Apply vertical velocity while held
RunService.Heartbeat:Connect(function()
	local char = player.Character
	if not char then return end
	local hrp  = char:FindFirstChild("HumanoidRootPart")
	if not hrp then return end
	if hrp.Position.Y >= 0 then
		holdUp   = false
		holdDown = false
		return
	end

	if holdUp then
		local lv = Instance.new("LinearVelocity", hrp)
		lv.VectorVelocity = Vector3.new(0, 22, 0)
		lv.MaxForce       = 1e5
		lv.RelativeTo     = Enum.ActuatorRelativeTo.World
		game:GetService("Debris"):AddItem(lv, 0.05)
	elseif holdDown then
		local lv = Instance.new("LinearVelocity", hrp)
		lv.VectorVelocity = Vector3.new(0, -16, 0)
		lv.MaxForce       = 1e5
		lv.RelativeTo     = Enum.ActuatorRelativeTo.World
		game:GetService("Debris"):AddItem(lv, 0.05)
	end
end)

-- ── MINE BUTTON ───────────────────────────────────────────────────────────────

mineBtn.Activated:Connect(function()
	-- Find nearest mineral node within 20 studs
	local char = player.Character
	if not char then return end
	local hrp  = char:FindFirstChild("HumanoidRootPart")
	if not hrp then return end

	local nodesFolder = workspace:FindFirstChild("MineralNodes")
	if not nodesFolder then return end

	local nearest, nearestDist = nil, 20
	for _, node in ipairs(nodesFolder:GetChildren()) do
		if not node:GetAttribute("NodeId") then continue end
		local dist = (node.Position - hrp.Position).Magnitude
		if dist < nearestDist then
			nearest     = node
			nearestDist = dist
		end
	end

	if nearest then
		Remotes.Get("MineNode"):FireServer(nearest)
	end
end)

-- ── SHOOT BUTTON ─────────────────────────────────────────────────────────────

shootBtn.Activated:Connect(function()
	local char = player.Character
	if not char then return end
	local hrp  = char:FindFirstChild("HumanoidRootPart")
	if not hrp then return end

	local creaturesFolder = workspace:FindFirstChild("Creatures")
	if not creaturesFolder then return end

	local nearest, nearestId = nil, nil
	local nearestDist = 80  -- shoot range
	for _, creaturePart in ipairs(creaturesFolder:GetChildren()) do
		local cid  = creaturePart:GetAttribute("CreatureId")
		if not cid then continue end
		local dist = (creaturePart.Position - hrp.Position).Magnitude
		if dist < nearestDist then
			nearest     = creaturePart
			nearestId   = cid
			nearestDist = dist
		end
	end

	if nearestId then
		Remotes.Get("ShootCreature"):FireServer(nearestId, 15)

		-- Flash the shoot button
		shootBtn.BackgroundColor3 = Color3.fromRGB(255, 100, 100)
		task.delay(0.15, function()
			shootBtn.BackgroundColor3 = Color3.fromRGB(180, 30, 30)
		end)
	end
end)

-- ── BUILD BUTTON ─────────────────────────────────────────────────────────────

buildBtn.Activated:Connect(function()
	local hud = playerGui:FindFirstChild("HUD")
	if not hud then return end
	local buildPanel = hud:FindFirstChild("BuildPanel")
	if buildPanel then
		buildPanel.Visible = not buildPanel.Visible
	end
end)

print("[MobileControls] Touch controls enabled.")
