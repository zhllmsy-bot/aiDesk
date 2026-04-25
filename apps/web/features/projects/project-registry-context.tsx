"use client";

const registry = [
  { id: "proj_atlas", name: "Atlas Control Plane" },
  { id: "proj_meridian", name: "Meridian Control Plane" },
];

export function useProjectRegistry() {
  return registry;
}
