-- HUD.client.lua
-- In-game HUD: resource bars, depth display, build menu, notifications
-- Place in StarterGui as a LocalScript inside a ScreenGui named "HUD"

local Players           = game:GetService("Players")
local TweenService      = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService        = game:GetService("RunService")

local GameConfig  = require(ReplicatedStorage:WaitForChild("GameConfig"))
local ModuleData  = require(ReplicatedStorage:WaitForChild("Modules"):WaitForChild("ModuleData"))
local Remotes     = require(ReplicatedStorage:WaitForChild("RemoteEvents"))

local player = Players.LocalPlayer
local gui    = script.Parent  -- ScreenGui "HUD"

-- ── BINDABLE EVENTS (for inter-script communication) ─────────────────────────
local resourceBind = Instance.new("BindableEvent", gui)
resourceBind.Name  = "ResourceUpdateBind"
local notifBind    = Instance.new("BindableEvent", gui)
notifBind.Name     = "NotifBind"

-- ── RESOURCE BAR BUILDER ──────────────────────────────────────────────────────

local function makeResourceBar(parent, name, icon, color, yPos)
	local frame            = Instance.new("Frame", parent)
	frame.Name             = name .. "Bar"
	frame.Size             = UDim2.new(0, 180, 0, 28)
	frame.Position         = UDim2.new(0, 10, 0, yPos)
	frame.BackgroundColor3 = Color3.fromRGB(10, 20, 50)
	frame.BorderSizePixel  = 0

	local corner           = Instance.new("UICorner", frame)
	corner.CornerRadius    = UDim.new(0, 6)

	local fill             = Instance.new("Frame", frame)
	fill.Name              = "Fill"
	fill.Size              = UDim2.new(1, 0, 1, 0)
	fill.BackgroundColor3  = color
	fill.BorderSizePixel   = 0
	local fillCorner       = Instance.new("UICorner", fill)
	fillCorner.CornerRadius = UDim.new(0, 6)

	local label            = Instance.new("TextLabel", frame)
	label.Name             = "Label"
	label.Size             = UDim2.new(1, 0, 1, 0)
	label.BackgroundTransparency = 1
	label.Text             = icon .. " " .. name .. ": 0"
	label.TextColor3       = Color3.new(1, 1, 1)
	label.TextScaled       = true
	label.Font             = Enum.Font.GothamBold
	label.ZIndex           = 2

	return frame
end

-- ── RESOURCE PANEL (top left) ─────────────────────────────────────────────────

local resPanel         = Instance.new("Frame", gui)
resPanel.Name          = "ResourcePanel"
resPanel.Size          = UDim2.new(0, 200, 0, 200)
resPanel.Position      = UDim2.new(0, 10, 0, 10)
resPanel.BackgroundTransparency = 1

local oxygenBar  = makeResourceBar(resPanel, "Oxygen",   "💨", Color3.fromRGB(100, 200, 255), 0)
local mineralBar = makeResourceBar(resPanel, "Minerals", "⛏️", Color3.fromRGB(180, 130, 80),  34)
local foodBar    = makeResourceBar(resPanel, "Food",     "🐟", Color3.fromRGB(100, 220, 100),  68)
local powerBar   = makeResourceBar(resPanel, "Power",    "⚡", Color3.fromRGB(255, 230, 0),   102)
local coinLabel  = Instance.new("TextLabel", resPanel)
coinLabel.Name   = "CoinLabel"
coinLabel.Size   = UDim2.new(0, 180, 0, 28)
coinLabel.Position = UDim2.new(0, 10, 0, 140)
coinLabel.BackgroundTransparency = 1
coinLabel.Text   = "💰 Coins: 0"
coinLabel.TextColor3 = Color3.fromRGB(255, 215, 0)
coinLabel.TextScaled = true
coinLabel.Font   = Enum.Font.GothamBold

-- ── DEPTH DISPLAY (top center) ────────────────────────────────────────────────

local depthLabel       = Instance.new("TextLabel", gui)
depthLabel.Name        = "DepthLabel"
depthLabel.Size        = UDim2.new(0, 200, 0, 40)
depthLabel.Position    = UDim2.new(0.5, -100, 0, 10)
depthLabel.BackgroundColor3 = Color3.fromRGB(5, 15, 50)
depthLabel.BackgroundTransparency = 0.4
depthLabel.Text        = "⬆ Surface"
depthLabel.TextColor3  = Color3.fromRGB(150, 220, 255)
depthLabel.TextScaled  = true
depthLabel.Font        = Enum.Font.GothamBold
local depthCorner      = Instance.new("UICorner", depthLabel)
depthCorner.CornerRadius = UDim.new(0, 8)

-- ── BUILD MENU (right side) ───────────────────────────────────────────────────

local buildPanel       = Instance.new("Frame", gui)
buildPanel.Name        = "BuildPanel"
buildPanel.Size        = UDim2.new(0, 220, 1, -20)
buildPanel.Position    = UDim2.new(1, -230, 0, 10)
buildPanel.BackgroundColor3 = Color3.fromRGB(5, 15, 45)
buildPanel.BackgroundTransparency = 0.2
buildPanel.Visible     = false
local bpCorner         = Instance.new("UICorner", buildPanel)
bpCorner.CornerRadius  = UDim.new(0, 10)

local buildTitle       = Instance.new("TextLabel", buildPanel)
buildTitle.Size        = UDim2.new(1, 0, 0, 40)
buildTitle.Position    = UDim2.new(0, 0, 0, 5)
buildTitle.BackgroundTransparency = 1
buildTitle.Text        = "🔧 BUILD"
buildTitle.TextColor3  = Color3.fromRGB(100, 220, 255)
buildTitle.TextScaled  = true
buildTitle.Font        = Enum.Font.GothamBold

local buildScroll      = Instance.new("ScrollingFrame", buildPanel)
buildScroll.Size       = UDim2.new(1, -10, 1, -60)
buildScroll.Position   = UDim2.new(0, 5, 0, 50)
buildScroll.BackgroundTransparency = 1
buildScroll.ScrollBarThickness = 4
buildScroll.CanvasSize = UDim2.new(0, 0, 0, 0)

local buildLayout      = Instance.new("UIListLayout", buildScroll)
buildLayout.Padding    = UDim.new(0, 6)
buildLayout.SortOrder  = Enum.SortOrder.Name

local function addBuildButton(modDef)
	local btn              = Instance.new("TextButton", buildScroll)
	btn.Name               = modDef.id
	btn.Size               = UDim2.new(1, -8, 0, 60)
	btn.BackgroundColor3   = Color3.fromRGB(10, 30, 70)
	btn.BorderSizePixel    = 0

	local bCorner          = Instance.new("UICorner", btn)
	bCorner.CornerRadius   = UDim.new(0, 8)

	local nameLabel        = Instance.new("TextLabel", btn)
	nameLabel.Size         = UDim2.new(1, -4, 0.5, 0)
	nameLabel.Position     = UDim2.new(0, 4, 0, 0)
	nameLabel.BackgroundTransparency = 1
	nameLabel.Text         = modDef.displayName
	nameLabel.TextColor3   = modDef.color
	nameLabel.TextScaled   = true
	nameLabel.Font         = Enum.Font.GothamBold
	nameLabel.TextXAlignment = Enum.TextXAlignment.Left

	-- Cost display
	local costParts = {}
	for res, amt in pairs(modDef.cost) do
		table.insert(costParts, amt .. " " .. res)
	end
	local costLabel        = Instance.new("TextLabel", btn)
	costLabel.Size         = UDim2.new(1, -4, 0.4, 0)
	costLabel.Position     = UDim2.new(0, 4, 0.55, 0)
	costLabel.BackgroundTransparency = 1
	costLabel.Text         = table.concat(costParts, "  |  ")
	costLabel.TextColor3   = Color3.fromRGB(180, 200, 180)
	costLabel.TextScaled   = true
	costLabel.Font         = Enum.Font.Gotham
	costLabel.TextXAlignment = Enum.TextXAlignment.Left

	btn.Activated:Connect(function()
		if _G.BuildingClient then
			_G.BuildingClient.EnterBuildMode(modDef.id)
			buildPanel.Visible = false
		end
	end)

	btn.MouseEnter:Connect(function()
		TweenService:Create(btn, TweenInfo.new(0.1), {
			BackgroundColor3 = Color3.fromRGB(20, 50, 110),
		}):Play()
	end)
	btn.MouseLeave:Connect(function()
		TweenService:Create(btn, TweenInfo.new(0.1), {
			BackgroundColor3 = Color3.fromRGB(10, 30, 70),
		}):Play()
	end)
end

-- Populate build buttons with Zone 1 modules initially
for _, modDef in pairs(ModuleData.Modules) do
	if modDef.requiredZone == 1 then
		addBuildButton(modDef)
	end
end

-- Update canvas size for scroll
buildLayout:GetPropertyChangedSignal("AbsoluteContentSize"):Connect(function()
	buildScroll.CanvasSize = UDim2.new(0, 0, 0, buildLayout.AbsoluteContentSize.Y + 10)
end)

-- ── BUILD TOGGLE BUTTON (bottom right) ───────────────────────────────────────

local buildToggle      = Instance.new("TextButton", gui)
buildToggle.Name       = "BuildToggle"
buildToggle.Size       = UDim2.new(0, 120, 0, 44)
buildToggle.Position   = UDim2.new(1, -135, 1, -58)
buildToggle.BackgroundColor3 = Color3.fromRGB(0, 140, 200)
buildToggle.Text       = "🔧 Build"
buildToggle.TextColor3 = Color3.new(1, 1, 1)
buildToggle.TextScaled = true
buildToggle.Font       = Enum.Font.GothamBold
local btCorner         = Instance.new("UICorner", buildToggle)
btCorner.CornerRadius  = UDim.new(0, 10)

buildToggle.Activated:Connect(function()
	buildPanel.Visible = not buildPanel.Visible
end)

-- ── RESOURCE UPDATE HANDLER ───────────────────────────────────────────────────

local maxValues = {
	Oxygen   = GameConfig.PlayerDefaults.MaxOxygen,
	Minerals = 9999,
	Food     = 9999,
	Power    = 9999,
}

local function updateBar(barFrame, value, max, icon, name)
	local pct  = math.clamp(value / math.max(1, max), 0, 1)
	TweenService:Create(barFrame.Fill, TweenInfo.new(0.3), {
		Size = UDim2.new(pct, 0, 1, 0),
	}):Play()
	barFrame.Label.Text = icon .. " " .. name .. ": " .. math.floor(value)
end

-- ── FLOATING GAIN TEXT ────────────────────────────────────────────────────────

local function spawnGainText(anchorFrame, text, color)
	local absPos  = anchorFrame.AbsolutePosition
	local absSize = anchorFrame.AbsoluteSize

	local lbl            = Instance.new("TextLabel", gui)
	lbl.Size             = UDim2.new(0, 110, 0, 26)
	lbl.Position         = UDim2.new(0, absPos.X + absSize.X + 6, 0, absPos.Y + 1)
	lbl.BackgroundTransparency = 1
	lbl.Text             = text
	lbl.TextColor3       = color
	lbl.TextStrokeColor3 = Color3.new(0, 0, 0)
	lbl.TextStrokeTransparency = 0.4
	lbl.TextScaled       = true
	lbl.Font             = Enum.Font.GothamBold
	lbl.ZIndex           = 30

	local targetY = absPos.Y - 52
	TweenService:Create(lbl, TweenInfo.new(1.4, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
		Position         = UDim2.new(0, absPos.X + absSize.X + 6, 0, targetY),
		TextTransparency = 1,
		TextStrokeTransparency = 1,
	}):Play()

	game:GetService("Debris"):AddItem(lbl, 1.5)
end

-- Tracks last known resource values to compute deltas
local prevRes = {}

resourceBind.Event:Connect(function(res)
	updateBar(oxygenBar,  res.Oxygen   or 0, maxValues.Oxygen,   "💨", "Oxygen")
	updateBar(mineralBar, res.Minerals or 0, maxValues.Minerals, "⛏️", "Minerals")
	updateBar(foodBar,    res.Food     or 0, maxValues.Food,     "🐟", "Food")
	updateBar(powerBar,   res.Power    or 0, maxValues.Power,    "⚡", "Power")
	coinLabel.Text = "💰 Coins: " .. math.floor(res.Coins or 0)

	-- Show floating gain texts for meaningful increases
	if next(prevRes) then
		local dOxy  = (res.Oxygen   or 0) - (prevRes.Oxygen   or 0)
		local dMin  = (res.Minerals or 0) - (prevRes.Minerals or 0)
		local dFood = (res.Food     or 0) - (prevRes.Food     or 0)
		local dPow  = (res.Power    or 0) - (prevRes.Power    or 0)
		local dCoin = (res.Coins    or 0) - (prevRes.Coins    or 0)

		if dOxy  >= 1 then spawnGainText(oxygenBar,  "+💨"..math.floor(dOxy),  Color3.fromRGB(100, 210, 255)) end
		if dMin  >= 1 then spawnGainText(mineralBar, "+⛏️"..math.floor(dMin),  Color3.fromRGB(210, 160, 90))  end
		if dFood >= 1 then spawnGainText(foodBar,    "+🐟"..math.floor(dFood), Color3.fromRGB(100, 230, 110)) end
		if dPow  >= 1 then spawnGainText(powerBar,   "+⚡"..math.floor(dPow),  Color3.fromRGB(255, 235, 60))  end
		if dCoin >= 1 then
			-- Coin gain floats near the coin label
			local absPos  = coinLabel.AbsolutePosition
			local absSize = coinLabel.AbsoluteSize
			local lbl     = Instance.new("TextLabel", gui)
			lbl.Size      = UDim2.new(0, 110, 0, 26)
			lbl.Position  = UDim2.new(0, absPos.X + absSize.X + 6, 0, absPos.Y + 1)
			lbl.BackgroundTransparency = 1
			lbl.Text      = "+💰"..math.floor(dCoin)
			lbl.TextColor3 = Color3.fromRGB(255, 225, 60)
			lbl.TextStrokeColor3 = Color3.new(0,0,0)
			lbl.TextStrokeTransparency = 0.4
			lbl.TextScaled = true
			lbl.Font       = Enum.Font.GothamBold
			lbl.ZIndex     = 30
			TweenService:Create(lbl, TweenInfo.new(1.4, Enum.EasingStyle.Quad, Enum.EasingDirection.Out), {
				Position = UDim2.new(0, absPos.X + absSize.X + 6, 0, absPos.Y - 50),
				TextTransparency = 1,
				TextStrokeTransparency = 1,
			}):Play()
			game:GetService("Debris"):AddItem(lbl, 1.5)
		end
	end

	prevRes = {
		Oxygen   = res.Oxygen   or 0,
		Minerals = res.Minerals or 0,
		Food     = res.Food     or 0,
		Power    = res.Power    or 0,
		Coins    = res.Coins    or 0,
	}
end)

-- ── AUTO-SAVE INDICATOR ───────────────────────────────────────────────────────

local saveLabel            = Instance.new("TextLabel", gui)
saveLabel.Name             = "SaveIndicator"
saveLabel.Size             = UDim2.new(0, 120, 0, 26)
saveLabel.Position         = UDim2.new(1, -135, 0, 60)
saveLabel.BackgroundTransparency = 1
saveLabel.Text             = "💾 Saved"
saveLabel.TextColor3       = Color3.fromRGB(80, 200, 120)
saveLabel.TextStrokeColor3 = Color3.new(0, 0, 0)
saveLabel.TextStrokeTransparency = 0.4
saveLabel.TextScaled       = true
saveLabel.Font             = Enum.Font.GothamBold
saveLabel.TextTransparency = 1
saveLabel.ZIndex           = 10

Remotes.Get("DataSaved").OnClientEvent:Connect(function()
	saveLabel.TextTransparency = 0
	TweenService:Create(saveLabel, TweenInfo.new(2, Enum.EasingStyle.Quad, Enum.EasingDirection.In, 0, false, 0.8), {
		TextTransparency = 1,
	}):Play()
end)

-- ── DEPTH DISPLAY (updated from PlayerController) ────────────────────────────

RunService.RenderStepped:Connect(function()
	local char = player.Character
	if not char then return end
	local hrp  = char:FindFirstChild("HumanoidRootPart")
	if not hrp then return end
	local depth = math.max(0, -hrp.Position.Y)
	if depth < 1 then
		depthLabel.Text = "⬆ Surface"
		depthLabel.TextColor3 = Color3.fromRGB(150, 220, 255)
	else
		-- Find zone name
		local zoneName = "Sunlight Zone"
		for i, zone in ipairs(GameConfig.Zones) do
			if depth >= zone.minDepth and depth < zone.maxDepth then
				zoneName = zone.name
			end
		end
		depthLabel.Text = string.format("↓ %.0fm  |  %s", depth, zoneName)
		depthLabel.TextColor3 = Color3.fromRGB(100, 180, 255)
	end
end)

-- ── NOTIFICATION SYSTEM ───────────────────────────────────────────────────────

local notifQueue = {}
local notifShowing = false

local NOTIF_COLORS = {
	info    = Color3.fromRGB(50, 120, 220),
	success = Color3.fromRGB(40, 180, 80),
	warning = Color3.fromRGB(220, 160, 0),
	danger  = Color3.fromRGB(200, 40, 40),
}

local function showNextNotif()
	if notifShowing or #notifQueue == 0 then return end
	notifShowing = true
	local data = table.remove(notifQueue, 1)

	local notif            = Instance.new("Frame", gui)
	notif.Name             = "Notification"
	notif.Size             = UDim2.new(0, 300, 0, 70)
	notif.Position         = UDim2.new(0.5, -150, 1, 10)
	notif.BackgroundColor3 = NOTIF_COLORS[data.type] or NOTIF_COLORS.info
	notif.BackgroundTransparency = 0.1
	notif.ZIndex           = 20
	local nCorner          = Instance.new("UICorner", notif)
	nCorner.CornerRadius   = UDim.new(0, 10)

	local titleLabel       = Instance.new("TextLabel", notif)
	titleLabel.Size        = UDim2.new(1, -10, 0.45, 0)
	titleLabel.Position    = UDim2.new(0, 5, 0, 4)
	titleLabel.BackgroundTransparency = 1
	titleLabel.Text        = data.title
	titleLabel.TextColor3  = Color3.new(1, 1, 1)
	titleLabel.TextScaled  = true
	titleLabel.Font        = Enum.Font.GothamBold
	titleLabel.ZIndex      = 21

	local msgLabel         = Instance.new("TextLabel", notif)
	msgLabel.Size          = UDim2.new(1, -10, 0.45, 0)
	msgLabel.Position      = UDim2.new(0, 5, 0.5, 0)
	msgLabel.BackgroundTransparency = 1
	msgLabel.Text          = data.message
	msgLabel.TextColor3    = Color3.fromRGB(220, 240, 255)
	msgLabel.TextScaled    = true
	msgLabel.Font          = Enum.Font.Gotham
	msgLabel.ZIndex        = 21

	-- Slide in
	TweenService:Create(notif, TweenInfo.new(0.3, Enum.EasingStyle.Back), {
		Position = UDim2.new(0.5, -150, 1, -90),
	}):Play()

	-- Auto-dismiss after 3.5s
	task.delay(3.5, function()
		TweenService:Create(notif, TweenInfo.new(0.3), {
			Position = UDim2.new(0.5, -150, 1, 10),
		}):Play()
		task.delay(0.35, function()
			notif:Destroy()
			notifShowing = false
			showNextNotif()
		end)
	end)
end

notifBind.Event:Connect(function(title, message, notifType)
	table.insert(notifQueue, { title = title, message = message, type = notifType or "info" })
	showNextNotif()
end)

-- Also handle server-pushed notifications
Remotes.Get("Notification").OnClientEvent:Connect(function(data)
	table.insert(notifQueue, data)
	showNextNotif()
end)

Remotes.Get("BaseUnderAttack").OnClientEvent:Connect(function()
	table.insert(notifQueue, {
		title   = "⚠ BASE UNDER ATTACK!",
		message = "Sea creatures are attacking your base!",
		type    = "danger",
	})
	showNextNotif()
end)

Remotes.Get("CreatureDied").OnClientEvent:Connect(function(cid, reward)
	local parts = {}
	for k, v in pairs(reward) do
		table.insert(parts, "+" .. v .. " " .. k)
	end
	table.insert(notifQueue, {
		title   = "Creature Defeated!",
		message = table.concat(parts, "  "),
		type    = "success",
	})
	showNextNotif()
end)
