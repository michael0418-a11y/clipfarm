-- UpgradeGui.client.lua
-- Click on any placed module in the world to open upgrade/remove panel
-- Place in StarterGui as a LocalScript inside a ScreenGui named "UpgradeGui"

local Players           = game:GetService("Players")
local TweenService      = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService  = game:GetService("UserInputService")

local ModuleData = require(ReplicatedStorage:WaitForChild("Modules"):WaitForChild("ModuleData"))
local Remotes    = require(ReplicatedStorage:WaitForChild("RemoteEvents"))

local player = Players.LocalPlayer
local mouse  = player:GetMouse()
local gui    = script.Parent

-- ── BUILD PANEL UI ────────────────────────────────────────────────────────────

local panel            = Instance.new("Frame", gui)
panel.Name             = "UpgradePanel"
panel.Size             = UDim2.new(0, 280, 0, 320)
panel.Position         = UDim2.new(0.5, -140, 0.5, -160)
panel.BackgroundColor3 = Color3.fromRGB(8, 20, 55)
panel.BackgroundTransparency = 0.05
panel.Visible          = false
panel.ZIndex           = 30

local corner = Instance.new("UICorner", panel)
corner.CornerRadius = UDim.new(0, 12)

local stroke = Instance.new("UIStroke", panel)
stroke.Color = Color3.fromRGB(0, 160, 255)
stroke.Thickness = 2

-- Title
local titleLabel    = Instance.new("TextLabel", panel)
titleLabel.Name     = "Title"
titleLabel.Size     = UDim2.new(1, -10, 0, 40)
titleLabel.Position = UDim2.new(0, 5, 0, 5)
titleLabel.BackgroundTransparency = 1
titleLabel.TextColor3 = Color3.fromRGB(100, 200, 255)
titleLabel.TextScaled = true
titleLabel.Font       = Enum.Font.GothamBold
titleLabel.ZIndex     = 31

-- Level label
local levelLabel    = Instance.new("TextLabel", panel)
levelLabel.Name     = "Level"
levelLabel.Size     = UDim2.new(1, -10, 0, 25)
levelLabel.Position = UDim2.new(0, 5, 0, 48)
levelLabel.BackgroundTransparency = 1
levelLabel.TextColor3 = Color3.fromRGB(180, 200, 220)
levelLabel.TextScaled = true
levelLabel.Font       = Enum.Font.Gotham
levelLabel.ZIndex     = 31

-- Stats label
local statsLabel    = Instance.new("TextLabel", panel)
statsLabel.Name     = "Stats"
statsLabel.Size     = UDim2.new(1, -20, 0, 70)
statsLabel.Position = UDim2.new(0, 10, 0, 78)
statsLabel.BackgroundTransparency = 1
statsLabel.TextColor3 = Color3.fromRGB(200, 220, 200)
statsLabel.TextScaled = true
statsLabel.TextWrapped = true
statsLabel.Font       = Enum.Font.Gotham
statsLabel.ZIndex     = 31

-- HP bar
local hpFrame       = Instance.new("Frame", panel)
hpFrame.Name        = "HPFrame"
hpFrame.Size        = UDim2.new(0.9, 0, 0, 18)
hpFrame.Position    = UDim2.new(0.05, 0, 0, 155)
hpFrame.BackgroundColor3 = Color3.fromRGB(20, 20, 20)
hpFrame.BorderSizePixel = 0
hpFrame.ZIndex      = 31
local hpFill        = Instance.new("Frame", hpFrame)
hpFill.Name         = "Fill"
hpFill.Size         = UDim2.new(1, 0, 1, 0)
hpFill.BackgroundColor3 = Color3.fromRGB(80, 200, 80)
hpFill.BorderSizePixel = 0
local hpLabel       = Instance.new("TextLabel", hpFrame)
hpLabel.Name        = "Label"
hpLabel.Size        = UDim2.new(1, 0, 1, 0)
hpLabel.BackgroundTransparency = 1
hpLabel.Text        = "HP: 100 / 100"
hpLabel.TextColor3  = Color3.new(1, 1, 1)
hpLabel.TextScaled  = true
hpLabel.Font        = Enum.Font.Gotham
hpLabel.ZIndex      = 32

-- Upgrade cost label
local upgradeCostLabel = Instance.new("TextLabel", panel)
upgradeCostLabel.Name  = "UpgradeCost"
upgradeCostLabel.Size  = UDim2.new(1, -20, 0, 25)
upgradeCostLabel.Position = UDim2.new(0, 10, 0, 180)
upgradeCostLabel.BackgroundTransparency = 1
upgradeCostLabel.TextColor3 = Color3.fromRGB(255, 200, 50)
upgradeCostLabel.TextScaled = true
upgradeCostLabel.Font       = Enum.Font.Gotham
upgradeCostLabel.ZIndex     = 31

-- Upgrade button
local upgradeBtn    = Instance.new("TextButton", panel)
upgradeBtn.Name     = "UpgradeBtn"
upgradeBtn.Size     = UDim2.new(0.55, 0, 0, 42)
upgradeBtn.Position = UDim2.new(0.05, 0, 0, 212)
upgradeBtn.BackgroundColor3 = Color3.fromRGB(0, 160, 80)
upgradeBtn.Text     = "⬆ Upgrade"
upgradeBtn.TextColor3 = Color3.new(1, 1, 1)
upgradeBtn.TextScaled = true
upgradeBtn.Font     = Enum.Font.GothamBold
upgradeBtn.ZIndex   = 31
local ubCorner = Instance.new("UICorner", upgradeBtn)
ubCorner.CornerRadius = UDim.new(0, 8)

-- Remove button
local removeBtn     = Instance.new("TextButton", panel)
removeBtn.Name      = "RemoveBtn"
removeBtn.Size      = UDim2.new(0.35, 0, 0, 42)
removeBtn.Position  = UDim2.new(0.62, 0, 0, 212)
removeBtn.BackgroundColor3 = Color3.fromRGB(180, 30, 30)
removeBtn.Text      = "🗑 Remove"
removeBtn.TextColor3 = Color3.new(1, 1, 1)
removeBtn.TextScaled = true
removeBtn.Font      = Enum.Font.GothamBold
removeBtn.ZIndex    = 31
local rbCorner = Instance.new("UICorner", removeBtn)
rbCorner.CornerRadius = UDim.new(0, 8)

-- Close button
local closeBtn      = Instance.new("TextButton", panel)
closeBtn.Name       = "CloseBtn"
closeBtn.Size       = UDim2.new(0, 30, 0, 30)
closeBtn.Position   = UDim2.new(1, -35, 0, 5)
closeBtn.BackgroundColor3 = Color3.fromRGB(60, 20, 20)
closeBtn.Text       = "✕"
closeBtn.TextColor3 = Color3.new(1, 1, 1)
closeBtn.TextScaled = true
closeBtn.Font       = Enum.Font.GothamBold
closeBtn.ZIndex     = 32
local cbCorner = Instance.new("UICorner", closeBtn)
cbCorner.CornerRadius = UDim.new(0, 6)

-- ── STATE ─────────────────────────────────────────────────────────────────────

local selectedInstanceId = nil
local selectedModDef     = nil

local function closePanel()
	TweenService:Create(panel, TweenInfo.new(0.15), { Size = UDim2.new(0, 0, 0, 0) }):Play()
	task.delay(0.16, function()
		panel.Visible = false
		panel.Size    = UDim2.new(0, 280, 0, 320)
	end)
	selectedInstanceId = nil
	selectedModDef     = nil
end

closeBtn.Activated:Connect(closePanel)

-- Close on Escape
UserInputService.InputBegan:Connect(function(input, processed)
	if processed then return end
	if input.KeyCode == Enum.KeyCode.Escape then closePanel() end
end)

-- ── OPEN PANEL FOR A MODULE ───────────────────────────────────────────────────

local function openPanel(instanceId, modDef, level, hp, maxHp)
	selectedInstanceId = instanceId
	selectedModDef     = modDef

	titleLabel.Text    = modDef.displayName
	levelLabel.Text    = "Level " .. level .. " / " .. modDef.maxLevel

	-- Stats summary
	local bonuses = modDef.levelBonuses and modDef.levelBonuses[level]
	local statLines = {}
	if bonuses then
		for k, v in pairs(bonuses) do
			table.insert(statLines, k .. ": " .. v)
		end
	end
	statsLabel.Text = table.concat(statLines, "\n")

	-- HP bar
	local pct = math.clamp(hp / math.max(1, maxHp), 0, 1)
	hpFill.Size = UDim2.new(pct, 0, 1, 0)
	hpFill.BackgroundColor3 = pct > 0.5 and Color3.fromRGB(80, 200, 80)
		or pct > 0.25 and Color3.fromRGB(220, 180, 0)
		or Color3.fromRGB(200, 40, 40)
	hpLabel.Text = "HP: " .. math.floor(hp) .. " / " .. maxHp

	-- Upgrade cost
	local nextLevel = level + 1
	if nextLevel <= modDef.maxLevel and modDef.upgradeCost and modDef.upgradeCost[nextLevel] then
		local costParts = {}
		for res, amt in pairs(modDef.upgradeCost[nextLevel]) do
			table.insert(costParts, amt .. " " .. res)
		end
		upgradeCostLabel.Text  = "Upgrade cost: " .. table.concat(costParts, " | ")
		upgradeBtn.Visible     = true
		upgradeBtn.BackgroundColor3 = Color3.fromRGB(0, 160, 80)
	else
		upgradeCostLabel.Text  = "MAX LEVEL"
		upgradeBtn.Visible     = false
	end

	-- Can't remove starter pod
	removeBtn.Visible = modDef.id ~= "StarterPod"

	panel.Visible = true
	panel.Size    = UDim2.new(0, 0, 0, 0)
	TweenService:Create(panel, TweenInfo.new(0.2, Enum.EasingStyle.Back), {
		Size = UDim2.new(0, 280, 0, 320),
	}):Play()
end

-- ── CLICK DETECTION ───────────────────────────────────────────────────────────

mouse.Button1Down:Connect(function()
	-- If in build mode, don't intercept
	if _G.BuildingClient and _G.BuildingClient.IsInBuildMode and _G.BuildingClient.IsInBuildMode() then return end

	local target = mouse.Target
	if not target then closePanel(); return end

	local instanceId = target:GetAttribute("InstanceId")
	local moduleId   = target:GetAttribute("ModuleId")
	if not instanceId or not moduleId then closePanel(); return end

	local modDef = ModuleData.Get(moduleId)
	if not modDef then closePanel(); return end

	local level  = target:GetAttribute("Level") or 1
	local hp     = target:GetAttribute("CurrentHP") or 100
	local maxHp  = target:GetAttribute("MaxHP") or 100

	openPanel(instanceId, modDef, level, hp, maxHp)
end)

-- ── BUTTONS ───────────────────────────────────────────────────────────────────

upgradeBtn.Activated:Connect(function()
	if not selectedInstanceId then return end
	Remotes.Get("UpgradeModule"):FireServer(selectedInstanceId)
	closePanel()
end)

removeBtn.Activated:Connect(function()
	if not selectedInstanceId then return end
	Remotes.Get("RemoveModule"):FireServer(selectedInstanceId)
	closePanel()
end)

-- ── LIVE HP UPDATES ───────────────────────────────────────────────────────────

Remotes.Get("ModuleDamaged").OnClientEvent:Connect(function(instanceId, newHp)
	if instanceId ~= selectedInstanceId then return end
	-- Find the part to get maxHp
	local target = workspace:FindFirstChild("Bases", true)
	local maxHp  = 100
	if target then
		for _, folder in ipairs(workspace.Bases:GetChildren()) do
			for _, part in ipairs(folder:GetChildren()) do
				if part:GetAttribute("InstanceId") == instanceId then
					maxHp = part:GetAttribute("MaxHP") or 100
					part:SetAttribute("CurrentHP", newHp)
					break
				end
			end
		end
	end
	local pct = math.clamp(newHp / math.max(1, maxHp), 0, 1)
	hpFill.Size = UDim2.new(pct, 0, 1, 0)
	hpFill.BackgroundColor3 = pct > 0.5 and Color3.fromRGB(80, 200, 80)
		or pct > 0.25 and Color3.fromRGB(220, 180, 0)
		or Color3.fromRGB(200, 40, 40)
	hpLabel.Text = "HP: " .. math.floor(newHp) .. " / " .. maxHp
end)

Remotes.Get("ModuleUpgraded").OnClientEvent:Connect(function(instanceId, newLevel)
	if instanceId ~= selectedInstanceId or not selectedModDef then return end
	levelLabel.Text = "Level " .. newLevel .. " / " .. selectedModDef.maxLevel
end)
