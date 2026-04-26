import * as React from "react";

import {
  Avatar,
  AvatarFallback,
  Badge,
  Breadcrumb,
  BreadcrumbCurrent,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
  Button,
  ButtonLink,
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  DescriptionItem,
  DescriptionList,
  Input,
  PageHeader,
  PageLayout,
  SearchInput,
  SegmentedControl,
  Select,
  Sidebar,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
  SidebarItem,
  SidebarNav,
  StatCard,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Textarea,
} from "./index";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  SheetTrigger,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Toast,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./primitives";

export default {
  title: "Design System/Primitives",
};

export function LightAndDark() {
  return (
    <TooltipProvider>
      <ToastProvider>
        <div className="ui-stack ui-stack-gap-4">
          <Button>Button</Button>
          <ButtonLink href="#button-link" variant="secondary">
            Button link
          </ButtonLink>
          <Input aria-label="Input" placeholder="Input" />
          <SearchInput aria-label="Search" placeholder="Search" />
          <Textarea aria-label="Textarea" placeholder="Textarea" />
          <Select aria-label="Select" defaultValue="one">
            <option value="one">One</option>
            <option value="two">Two</option>
          </Select>
          <Badge tone="success">Badge</Badge>
          <Card>
            <CardHeader>
              <strong>Card header</strong>
            </CardHeader>
            <CardBody>Card body</CardBody>
            <CardFooter>Card footer</CardFooter>
          </Card>
          <StatCard label="Pending queue" value="3" description="Requests awaiting review." />
          <SegmentedControl
            aria-label="Status"
            onValueChange={() => undefined}
            options={[
              { label: "All", value: "all" },
              { label: "Pending", value: "pending" },
            ]}
            value="all"
          />
          <DescriptionList>
            <DescriptionItem label="Requester" value="Admin Operator" />
            <DescriptionItem label="Run" value="run_20260419_main" />
          </DescriptionList>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink href="#workspace">Workspace</BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbItem>
                <BreadcrumbSeparator />
                <BreadcrumbCurrent>Review</BreadcrumbCurrent>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
          <Avatar>
            <AvatarFallback>AO</AvatarFallback>
          </Avatar>
          <PageHeader
            breadcrumb={
              <Breadcrumb>
                <BreadcrumbList>
                  <BreadcrumbItem>
                    <BreadcrumbLink href="#workspace">Workspace</BreadcrumbLink>
                  </BreadcrumbItem>
                </BreadcrumbList>
              </Breadcrumb>
            }
            description="Approve, reject, or inspect the decisions that can change an autonomous run."
            title="Decision queue"
          />
          <PageLayout>
            <Sidebar>
              <SidebarHeader>Sidebar</SidebarHeader>
              <SidebarNav aria-label="Demo">
                <SidebarGroup label="Workspace">
                  <SidebarItem
                    active
                    href="#control"
                    label="Control"
                    description="Project queue."
                  />
                </SidebarGroup>
              </SidebarNav>
              <SidebarFooter>Footer</SidebarFooter>
            </Sidebar>
          </PageLayout>
          <Dialog>
            <DialogTrigger asChild>
              <Button tone="secondary">Dialog</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogTitle>Dialog title</DialogTitle>
              <DialogDescription>Dialog description</DialogDescription>
            </DialogContent>
          </Dialog>
          <Sheet>
            <SheetTrigger asChild>
              <Button tone="ghost">Sheet</Button>
            </SheetTrigger>
            <SheetContent>
              <SheetTitle>Sheet title</SheetTitle>
              <SheetDescription>Sheet description</SheetDescription>
            </SheetContent>
          </Sheet>
          <Tabs defaultValue="one">
            <TabsList>
              <TabsTrigger value="one">One</TabsTrigger>
              <TabsTrigger value="two">Two</TabsTrigger>
            </TabsList>
            <TabsContent value="one">Panel one</TabsContent>
            <TabsContent value="two">Panel two</TabsContent>
          </Tabs>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button tone="ghost">Tooltip</Button>
            </TooltipTrigger>
            <TooltipContent>Tooltip content</TooltipContent>
          </Tooltip>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Column</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell>Cell</TableCell>
              </TableRow>
            </TableBody>
          </Table>
          <Toast open>
            <ToastTitle>Toast title</ToastTitle>
            <ToastDescription>Toast description</ToastDescription>
          </Toast>
          <ToastViewport />
        </div>
      </ToastProvider>
    </TooltipProvider>
  );
}
