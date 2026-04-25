import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import {
  Badge,
  Button,
  Input,
  Select,
  Table,
  TableBody,
  TableCell,
  TableRow,
  Textarea,
} from "@ai-desk/ui";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Toast,
  ToastProvider,
  ToastTitle,
  ToastViewport,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@ai-desk/ui/primitives";

describe("ui primitives", () => {
  it("renders the first ten primitives and preserves keyboard behavior", async () => {
    render(
      <TooltipProvider>
        <ToastProvider>
          <Button>Submit</Button>
          <Input aria-label="Name" />
          <Textarea aria-label="Notes" />
          <Select aria-label="Mode" defaultValue="safe">
            <option value="safe">Safe</option>
          </Select>
          <Badge>Ready</Badge>
          <Dialog>
            <DialogTrigger asChild>
              <Button>Open dialog</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogTitle>Approval dialog</DialogTitle>
              <DialogDescription>Approve the current run.</DialogDescription>
            </DialogContent>
          </Dialog>
          <Sheet>
            <SheetTrigger asChild>
              <Button>Open sheet</Button>
            </SheetTrigger>
            <SheetContent>
              <SheetTitle>Run sheet</SheetTitle>
            </SheetContent>
          </Sheet>
          <Tabs defaultValue="timeline">
            <TabsList>
              <TabsTrigger value="timeline">Timeline</TabsTrigger>
              <TabsTrigger value="graph">Graph</TabsTrigger>
            </TabsList>
            <TabsContent value="timeline">Timeline panel</TabsContent>
            <TabsContent value="graph">Graph panel</TabsContent>
          </Tabs>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button>Inspect</Button>
            </TooltipTrigger>
            <TooltipContent>Inspect run</TooltipContent>
          </Tooltip>
          <Table>
            <TableBody>
              <TableRow>
                <TableCell>Cell</TableCell>
              </TableRow>
            </TableBody>
          </Table>
          <Toast open>
            <ToastTitle>Saved</ToastTitle>
          </Toast>
          <ToastViewport />
        </ToastProvider>
      </TooltipProvider>,
    );

    await userEvent.click(screen.getByRole("button", { name: "Open dialog" }));
    expect(screen.getByRole("dialog", { name: "Approval dialog" })).toBeVisible();

    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Approval dialog" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: "Graph" }));
    expect(screen.getByText("Graph panel")).toBeVisible();

    expect(screen.getByRole("button", { name: "Submit" })).toHaveAttribute(
      "data-testid",
      "ui-button",
    );
    expect(screen.getByLabelText("Name")).toBeVisible();
    expect(screen.getByLabelText("Notes")).toBeVisible();
    expect(screen.getByLabelText("Mode")).toBeVisible();
    expect(screen.getByText("Ready")).toBeVisible();
    expect(screen.getByText("Cell")).toBeVisible();
    expect(screen.getByText("Saved")).toBeVisible();
  });
});
