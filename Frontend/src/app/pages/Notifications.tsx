import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Switch } from "../components/ui/switch";
import { Label } from "../components/ui/label";
import {
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  FileText,
  Calendar,
  Check,
} from "lucide-react";

const notifications = [
  {
    id: 1,
    type: "warning",
    title: "Quiz Performance Alert",
    message: "Your score in Physics Quiz #5 (65%) was below your average of 78%",
    time: "2 hours ago",
    read: false,
  },
  {
    id: 2,
    type: "info",
    title: "Study Plan Updated",
    message: "Your study plan has been adjusted based on recent performance in Integration Techniques",
    time: "5 hours ago",
    read: false,
  },
  {
    id: 3,
    type: "success",
    title: "New Materials Processed",
    message: "3 Computer Science documents are ready for review and personalized learning support",
    time: "1 day ago",
    read: false,
  },
  {
    id: 4,
    type: "reminder",
    title: "Study Session Reminder",
    message: "You have a study session scheduled for Machine Learning at 2:00 PM today",
    time: "1 day ago",
    read: true,
  },
  {
    id: 5,
    type: "success",
    title: "Mastery Milestone Reached",
    message: "Congratulations! You've achieved 90% mastery in Data Structures",
    time: "2 days ago",
    read: true,
  },
  {
    id: 6,
    type: "info",
    title: "Quiz Available",
    message: "A new adaptive quiz has been generated for Organic Chemistry",
    time: "3 days ago",
    read: true,
  },
];

const notificationSettings = [
  { id: "study-reminders", label: "Study Reminders", enabled: true },
  { id: "weak-topics", label: "Weak Topic Alerts", enabled: true },
  { id: "quiz-notifications", label: "Quiz Notifications", enabled: true },
  { id: "progress-updates", label: "Progress Updates", enabled: false },
  { id: "plan-changes", label: "Study Plan Changes", enabled: true },
  { id: "material-processed", label: "New Materials Processed", enabled: true },
];

export default function Notifications() {
  const unreadCount = notifications.filter((n) => !n.read).length;

  const getIcon = (type: string) => {
    switch (type) {
      case "warning":
        return <AlertTriangle className="w-5 h-5 text-warning" />;
      case "success":
        return <CheckCircle2 className="w-5 h-5 text-green-600" />;
      case "reminder":
        return <Calendar className="w-5 h-5 text-blue-600" />;
      default:
        return <TrendingUp className="w-5 h-5 text-blue-600" />;
    }
  };

  const getBgColor = (type: string) => {
    switch (type) {
      case "warning":
        return "bg-warning/10";
      case "success":
        return "bg-green-100";
      case "reminder":
        return "bg-blue-100";
      default:
        return "bg-blue-100";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl mb-2">Notifications</h1>
          <p className="text-muted-foreground">
            Stay updated with your learning progress and reminders
          </p>
        </div>
        {unreadCount > 0 && (
          <Button variant="outline">
            <Check className="w-4 h-4 mr-2" />
            Mark All as Read
          </Button>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr,350px]">
        {/* Notifications List */}
        <div className="space-y-3">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg">Recent Notifications</h2>
            {unreadCount > 0 && (
              <Badge variant="default">{unreadCount} unread</Badge>
            )}
          </div>

          {notifications.map((notification) => (
            <Card
              key={notification.id}
              className={`transition-all ${
                !notification.read ? "border-primary/50 shadow-sm" : ""
              }`}
            >
              <CardContent className="p-4">
                <div className="flex gap-4">
                  <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center ${getBgColor(notification.type)}`}>
                    {getIcon(notification.type)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-1">
                      <h3 className="font-medium">{notification.title}</h3>
                      {!notification.read && (
                        <div className="w-2 h-2 rounded-full bg-primary ml-2 mt-1.5" />
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">
                      {notification.message}
                    </p>
                    <div className="flex items-center justify-between">
                      <p className="text-xs text-muted-foreground">{notification.time}</p>
                      {!notification.read && (
                        <Button variant="ghost" size="sm">
                          Mark as Read
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Notification Settings */}
        <div>
          <Card>
            <CardContent className="p-6">
              <h3 className="font-medium mb-4">Notification Preferences</h3>
              <div className="space-y-4">
                {notificationSettings.map((setting) => (
                  <div key={setting.id} className="flex items-center justify-between">
                    <Label htmlFor={setting.id} className="cursor-pointer">
                      {setting.label}
                    </Label>
                    <Switch id={setting.id} defaultChecked={setting.enabled} />
                  </div>
                ))}
              </div>
              <Button className="w-full mt-6">Save Preferences</Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
