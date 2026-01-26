/**
 * Generic Dashboard Component
 * Loads and renders dashboard configuration from backend
 * NO HARDCODES - Everything from database
 */

import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { apiClient } from "../services/api";
import { GenericWidget } from "./GenericWidget";
import "./generic-components.css";

interface UiSection {
  id: string;
  slug: string;
  label: string;
  description?: string;
  icon?: string;
  position: number;
  active: boolean;
  show_in_menu: boolean;
  role_restrictions?: string[];
  module_requirement?: string;
}

interface DashboardProps {
  dashboardSlug?: string;
  onSectionChange?: (section: UiSection) => void;
}

export function GenericDashboard({
  dashboardSlug = "default",
  onSectionChange,
}: DashboardProps) {
  const { user } = useAuth();
  const [sections, setSections] = useState<UiSection[]>([]);
  const [activeSection, setActiveSection] = useState<UiSection | null>(null);
  const [widgets, setWidgets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load sections on mount
  useEffect(() => {
    loadSections();
  }, []);

  // Load widgets when section changes
  useEffect(() => {
    if (activeSection) {
      loadWidgets(activeSection.id);
      onSectionChange?.(activeSection);
    }
  }, [activeSection, onSectionChange]);

  const loadSections = async () => {
    try {
      setLoading(true);
      const data = await apiClient.uiConfig.getSections({
        active_only: true,
      });
      setSections(data);

      // Set first section as active
      if (data.length > 0) {
        setActiveSection(data[0]);
      }
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load sections"
      );
      console.error("Error loading sections:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadWidgets = async (sectionId: string) => {
    try {
      const data = await apiClient.uiConfig.getWidgetsBySection(sectionId, {
        active_only: true,
      });
      setWidgets(data);
    } catch (err) {
      console.error("Error loading widgets:", err);
      setWidgets([]);
    }
  };

  if (loading) {
    return (
      <div className="generic-dashboard loading">
        <div className="spinner">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="generic-dashboard error">
        <div className="error-message">{error}</div>
        <button onClick={loadSections}>Retry</button>
      </div>
    );
  }

  if (sections.length === 0) {
    return (
      <div className="generic-dashboard empty">
        <p>No sections configured</p>
      </div>
    );
  }

  return (
    <div className="generic-dashboard">
      {/* Sections Navigation */}
      <nav className="dashboard-sections-nav">
        <div className="sections-tabs">
          {sections.map((section) => (
            <button
              key={section.id}
              className={`section-tab ${activeSection?.id === section.id ? "active" : ""}`}
              onClick={() => setActiveSection(section)}
              title={section.description}
            >
              {section.icon && <span className="section-icon">{section.icon}</span>}
              <span className="section-label">{section.label}</span>
            </button>
          ))}
        </div>
      </nav>

      {/* Widgets Grid */}
      {activeSection && (
        <div className="dashboard-section">
          <div className="section-header">
            <h1>{activeSection.label}</h1>
            {activeSection.description && (
              <p className="section-description">{activeSection.description}</p>
            )}
          </div>

          <div className="widgets-grid">
            {widgets.length > 0 ? (
              widgets.map((widget, index) => (
                <div
                  key={widget.id || index}
                  className={`widget-container width-${widget.width}`}
                >
                  <GenericWidget widget={widget} />
                </div>
              ))
            ) : (
              <div className="no-widgets">No widgets configured for this section</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default GenericDashboard;
