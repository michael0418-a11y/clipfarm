-- BossAnnouncerClient.client.lua
-- Full-screen boss spawn and defeat announcements
-- Place in StarterGui as a LocalScript inside a ScreenGui named "BossAnnouncerClient"

local TweenService      = game:GetService("TweenService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players           = game:GetService("Players")

local player = Players.LocalPlayer
local gui    = script.Parent

-- Wait for remote to exist
local remotes = ReplicatedStorage:WaitForChild("Remotes", 30)
if not remotes then return end
local BossAnnounce = remotes:WaitForChild("BossAnnounce", 30)
if not BossAnnounce then return end

-- ── BANNER BUILDER ────────────────────────────────────────────────────────────

local function showBanner(title, subtitle, color, duration)
	local banner            = Instance.new("Frame", gui)
	banner.Size             = UDim2.new(1, 0, 0, 0)
	banner.Position         = UDim2.new(0, 0, 0.3, 0)
	banner.BackgroundColor3 = color
	banner.BackgroundTransparency = 0.15
	banner.ZIndex           = 50
	banner.ClipsDescendants = true

	local gradient           = Instance.new("UIGradient", banner)
	gradient.Transparency    = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 0.6),
		NumberSequenceKeypoint.new(0.5, 0),
		NumberSequenceKeypoint.new(1, 0.6),
	})

	local titleLbl           = Instance.new("TextLabel", banner)
	titleLbl.Size            = UDim2.new(1, 0, 0, 60)
	titleLbl.Position        = UDim2.new(0, 0, 0, 10)
	titleLbl.BackgroundTransparency = 1
	titleLbl.Text            = title
	titleLbl.TextColor3      = Color3.new(1, 1, 1)
	titleLbl.TextScaled      = true
	titleLbl.Font            = Enum.Font.GothamBold
	titleLbl.ZIndex          = 51
	titleLbl.TextTransparency = 1

	local subLbl             = Instance.new("TextLabel", banner)
	subLbl.Size              = UDim2.new(1, 0, 0, 36)
	subLbl.Position          = UDim2.new(0, 0, 0, 74)
	subLbl.BackgroundTransparency = 1
	subLbl.Text              = subtitle
	subLbl.TextColor3        = Color3.fromRGB(220, 220, 255)
	subLbl.TextScaled        = true
	subLbl.Font              = Enum.Font.Gotham
	subLbl.ZIndex            = 51
	subLbl.TextTransparency  = 1

	-- Slide in
	TweenService:Create(banner, TweenInfo.new(0.4, Enum.EasingStyle.Back), {
		Size = UDim2.new(1, 0, 0, 120),
	}):Play()
	task.delay(0.1, function()
		TweenService:Create(titleLbl, TweenInfo.new(0.4), { TextTransparency = 0 }):Play()
		TweenService:Create(subLbl,   TweenInfo.new(0.5), { TextTransparency = 0 }):Play()
	end)

	-- Fade out
	task.delay(duration or 4, function()
		TweenService:Create(banner, TweenInfo.new(0.5), {
			Size = UDim2.new(1, 0, 0, 0),
			BackgroundTransparency = 1,
		}):Play()
		TweenService:Create(titleLbl, TweenInfo.new(0.4), { TextTransparency = 1 }):Play()
		TweenService:Create(subLbl,   TweenInfo.new(0.4), { TextTransparency = 1 }):Play()
		task.delay(0.6, function() banner:Destroy() end)
	end)
end

-- ── COUNTDOWN LABEL ───────────────────────────────────────────────────────────

local function showCountdown(bossName, seconds)
	local countLabel         = Instance.new("TextLabel", gui)
	countLabel.Size          = UDim2.new(0, 300, 0, 40)
	countLabel.Position      = UDim2.new(0.5, -150, 0.2, 0)
	countLabel.BackgroundColor3 = Color3.fromRGB(60, 0, 20)
	countLabel.BackgroundTransparency = 0.2
	countLabel.TextColor3    = Color3.fromRGB(255, 80, 80)
	countLabel.TextScaled    = true
	countLabel.Font          = Enum.Font.GothamBold
	countLabel.ZIndex        = 50
	local cCorner            = Instance.new("UICorner", countLabel)
	cCorner.CornerRadius     = UDim.new(0, 8)

	local remaining = seconds
	local conn
	conn = game:GetService("RunService").Heartbeat:Connect(function(dt)
		remaining = remaining - dt
		if remaining <= 0 then
			countLabel:Destroy()
			conn:Disconnect()
			return
		end
		countLabel.Text = "⚠ " .. bossName .. " in " .. math.ceil(remaining) .. "s"
	end)
end

-- ── LISTEN ────────────────────────────────────────────────────────────────────

BossAnnounce.OnClientEvent:Connect(function(data)
	if data.countdown then
		-- Boss arriving soon
		showCountdown(data.bossName, data.countdown)
		showBanner(
			"⚠  " .. data.bossName .. "  APPROACHING",
			"Prepare your defenses!",
			Color3.fromRGB(120, 0, 0),
			5
		)

	elseif data.defeated then
		-- Boss defeated
		local isYou = data.playerName == player.Name
		showBanner(
			"💀  " .. data.bossName .. "  DEFEATED",
			isYou and "You slew the beast! Rewards collected!" or data.playerName .. " defeated " .. data.bossName .. "!",
			Color3.fromRGB(0, 100, 0),
			5
		)

	else
		-- Boss spawned
		local isYou = data.playerName == player.Name
		showBanner(
			"💀  " .. data.bossName .. "  HAS ARRIVED",
			isYou and "Your base is under siege!" or data.playerName .. "'s base is under attack!",
			Color3.fromRGB(100, 0, 0),
			6
		)
	end
end)
